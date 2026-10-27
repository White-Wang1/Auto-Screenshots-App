#!/usr/bin/env python3
"""
本机会议截屏自动生成 PPT 工具
================================
独立运行的桌面脚本：实时捕获本机屏幕，检测到画面发生明显变化时自动截图，
结束后将截图按时间顺序铺满生成宽屏(16:9)PPT 并保存到本地。

用法:
    python scripts/screen_capture_ppt.py [--interval 0.5] [--threshold 5] \
        [--output ./output] [--duration 3600] [--scale 0.5]

参数:
    --interval   采样间隔(秒)，默认 0.5，越小越灵敏但更耗资源
    --threshold  屏幕变化判定阈值(相邻帧降采样灰度平均像素差)，默认 2.0，越小越敏感
    --output     保存目录，默认 ./output
    --duration   最大运行时长(秒)，默认 None(持续运行直到按 Ctrl+C 结束)
    --scale      截图缩放比例(0~1)，用于降低内存，默认 1.0(不缩放)

结束方式:
    1. 运行期间按 Ctrl+C 随时结束并自动生成 PPT
    2. 或等待 --duration 到达后自动结束
"""
import argparse
import logging
import os
import signal
import sys
import time
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageGrab
from pptx import Presentation
from pptx.util import Inches

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
logger = logging.getLogger("screen_capture_ppt")

# 宽屏PPT画布尺寸(16:9)
SLIDE_WIDTH_IN = 13.333
SLIDE_HEIGHT_IN = 7.5
# 用于变化比较的降采样尺寸
COMPARE_WIDTH = 160
COMPARE_HEIGHT = 90


def capture_screen() -> np.ndarray:
    """捕获当前屏幕画面，返回 BGR 格式的 numpy 数组。"""
    try:
        from mss import MSS
        with MSS() as sct:
            # 取主显示器（或所有显示器的合并区域）
            monitor = sct.monitors[1]
            shot = sct.grab(monitor)
        img = np.asarray(shot)
        # mss 输出为 BGRA，转 BGR
        return img[:, :, :3].copy()
    except Exception:
        # 回退到 PIL.ImageGrab（Windows/Mac/Linux X 均可）
        pil_img = ImageGrab.grab()
        return cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)


def compute_change(bgr_frame: np.ndarray, prev_gray: np.ndarray, scale: float) -> Tuple[float, np.ndarray]:
    """计算当前帧与上一参考帧的画面变化度，并返回当前帧的降采样灰度图。"""
    if scale < 1.0:
        new_w = max(1, int(bgr_frame.shape[1] * scale))
        new_h = max(1, int(bgr_frame.shape[0] * scale))
        bgr_frame = cv2.resize(bgr_frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (COMPARE_WIDTH, COMPARE_HEIGHT), interpolation=cv2.INTER_AREA).astype(np.float32)
    if prev_gray is None:
        return 0.0, small
    diff = cv2.absdiff(small, prev_gray)
    return float(cv2.mean(diff)[0]), small


def fit_cover(slide_w: int, slide_h: int, img_w: int, img_h: int) -> Tuple[int, int, int, int]:
    """以铺满画面的方式计算图片放置位置(留边白色充满)。"""
    ratio_w = slide_w / img_w
    ratio_h = slide_h / img_h
    scale = max(ratio_w, ratio_h)
    width = int(img_w * scale)
    height = int(img_h * scale)
    left = int((slide_w - width) / 2)
    top = int((slide_h - height) / 2)
    return left, top, width, height


def build_ppt(screenshot_paths: List[str], out_path: str) -> None:
    """将截图按顺序铺满生成16:9 PPT并保存到本地。"""
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_WIDTH_IN)
    prs.slide_height = Inches(SLIDE_HEIGHT_IN)
    blank = prs.slide_layouts[6]

    if not screenshot_paths:
        slide = prs.slides.add_slide(blank)
        slide.shapes.title.text = "本次会议未检测到有效的屏幕变化画面"
    else:
        for path in screenshot_paths:
            try:
                with Image.open(path) as im:
                    img_w, img_h = im.size
            except Exception as e:
                logger.warning("读取图片尺寸失败 %s: %s", path, e)
                img_w, img_h = int(SLIDE_WIDTH_IN * 96), int(SLIDE_HEIGHT_IN * 96)
            slide = prs.slides.add_slide(blank)
            left, top, width, height = fit_cover(
                int(prs.slide_width), int(prs.slide_height), img_w, img_h
            )
            slide.shapes.add_picture(path, left, top, width=width, height=height)

    prs.save(out_path)
    logger.info("PPT 已保存到: %s", out_path)


class ScreenCapturePpt:
    def __init__(self, interval: float, threshold: float, output_dir: str, scale: float):
        self.interval = interval
        self.threshold = threshold
        self.output_dir = output_dir
        self.scale = scale
        self.frame_dir = os.path.join(output_dir, "frames")
        self.screenshots: List[str] = []
        self.running = True
        os.makedirs(self.frame_dir, exist_ok=True)
        signal.signal(signal.SIGINT, self._stop)
        signal.signal(signal.SIGTERM, self._stop)

    def _stop(self, *args):  # type: ignore
        self.running = False
        logger.info("收到结束信号，准备生成 PPT ...")

    def run(self, duration: Optional[float]) -> None:
        prev_gray: Optional[np.ndarray] = None
        first_saved = False
        start = time.time()
        index = 0
        logger.info("开始实时捕获屏幕（间隔 %.1fs，变化阈值 %.1f）...", self.interval, self.threshold)
        logger.info("按 Ctrl+C 可随时结束。")
        while self.running:
            try:
                frame = capture_screen()
            except Exception as e:
                logger.error("屏幕捕获失败: %s", e)
                break

            change, prev_gray = compute_change(frame, prev_gray, self.scale)
            # 首帧始终保存；之后只有画面变化超过阈值才保存
            if not first_saved or change >= self.threshold:
                first_saved = True
                index += 1
                path = os.path.join(self.frame_dir, f"shot_{index:04d}.png")
                cv2.imwrite(path, frame)
                self.screenshots.append(path)
                if change >= self.threshold or index == 1:
                    logger.info("画面变化(差异 %.1f)，已保存 %s", change, path)

            if duration and (time.time() - start) >= duration:
                logger.info("已达到设定运行时长 %.1f 秒，结束。", duration)
                break
            time.sleep(self.interval)

        if not self.screenshots:
            logger.warning("未捕获到任何截图，跳过生成PPT。")
            return
        ppt_path = os.path.join(self.output_dir, "meeting_screenshots.pptx")
        build_ppt(self.screenshots, ppt_path)
        logger.info("完成：共捕获 %d 次画面变化，PPT 路径 %s", len(self.screenshots), ppt_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="本机会议截屏自动生成PPT")
    parser.add_argument("--interval", type=float, default=0.5, help="采样间隔(秒)，默认0.5")
    parser.add_argument("--threshold", type=float, default=2.0, help="屏幕变化判定阈值，默认2.0")
    parser.add_argument("--output", type=str, default="./output", help="保存目录，默认 ./output")
    parser.add_argument("--duration", type=float, default=None, help="最大运行时长(秒)，默认持续运行")
    parser.add_argument("--scale", type=float, default=1.0, help="截图缩放比例(0~1)，默认1.0")
    args = parser.parse_args()

    runner = ScreenCapturePpt(
        interval=args.interval,
        threshold=args.threshold,
        output_dir=os.path.abspath(args.output),
        scale=args.scale,
    )
    runner.run(args.duration)


if __name__ == "__main__":
    sys.exit(main())