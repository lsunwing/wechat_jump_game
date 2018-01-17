# -*- coding: utf-8 -*-

"""
=== 思路 ===
核心:通过截图, 计算得出棋子的位置和目标点的距离,
     根据两个点的距离乘以一个时间系数获得按压屏幕的时长

起点:棋子的颜色和大小是固定的,只要找到棋子头顶中心点坐标就能得到棋子的底座位置

落点:根据色差来定位,底色每一行都是基本一致的,偶尔会有一个数值的差异,所以在判断的时候不能精准判断
     如果棋子当前的落点是中心点,则下个目标块中心点会有白色提示点(245,245,245),利用这个特性可以精准找到落点位置
     如果棋子当前的落点不是中心点,则默认一个下移数值求落点位置
"""

from __future__ import print_function, division

import os
import sys
import math
import time
import random

from PIL import Image
try:
    from common import debug, config, screenshot
except Exception as ex:
    print(ex)
    print('请将脚本放在项目根目录中运行')
    print('请检查项目根目录中的 common 文件夹是否存在')
    exit(-1)

press_coefficient = 1.392

def yes_or_no(prompt, true_value='y', false_value='n', default=True):
    """
    检查是否已经为启动程序做好了准备
    """
    default_value = true_value if default else false_value
    prompt = '{} {}/{} [{}]: '.format(prompt, true_value,
        false_value, default_value)
    i = input(prompt)
    if not i:
        return default
    while True:
        if i == true_value:
            return True
        elif i == false_value:
            return False
        prompt = 'Please input {} or {}: '.format(true_value, false_value)
        i = input(prompt)

def find_piece_and_board(im):
    b_x = 0
    b_y = 0
    p_x = 0
    p_y = 0
    w, h = im.size
    im_pixel = im.load()

    # 找棋子基座的位置, b_x, b_y
    # 从中线向两边查找, 如果棋子在左边, 目标位置一定在右边, 如果棋子在右边, 目标位置一定在左边
    # 默认棋子顶点到基座的距离为190
    for y in range(700, h):
        pixel_line = im_pixel[0, y]
        for x in range(w//2, w):
            pixel_left = im_pixel[w - x, y]
            pixel_right = im_pixel[x, y]
            if 50 < pixel_left[0] < 55 and 50 < pixel_left[1] < 55 and 57 < pixel_left[2] < 62:
                # 左侧找到棋子, 棋子顶层有8个像素的色块
                b_x = w - x - 4
                b_y = y + 190
                break
            elif 50 < pixel_right[0] < 55 and 50 < pixel_right[1] < 55 and 57 < pixel_right[2] < 62:
                # 右侧找到棋子, 棋子顶层有8个像素的色块
                b_x = x + 4
                b_y = y + 190
                break

        if b_x:
            break
    print("ball position:", b_x, b_y)

    # 找目标位置
    # 如果棋子在左边, 从右向左扫描, 扫描至中线处, 如果棋子在右边, 从左向右扫描, 同样只扫描到中线处
    # 这个循环可以跟上面循环揉到一起, 减少扫描次数, 但判断条件要复杂
    for y in range(700, b_y):
        pixel_line = im_pixel[w - 1 if b_x > w//2 else 0, y]
        for x in range(0 if b_x > w//2 else w - 1, w//2, 1 if b_x > w//2 else -1):
            pixel = im_pixel[x, y]
            chk0 = abs(pixel[0] - pixel_line[0])
            chk1 = abs(pixel[1] - pixel_line[1])
            chk2 = abs(pixel[2] - pixel_line[2])
            # 底色可能存在一个数值的差异(233,61,155) / (232,61,155), 所以要范围匹配
            if (chk0 > 1 or chk1 > 1 or chk2 > 1) and p_x == 0:
                # 找到差异颜色暂不停止扫描, 等全部差异颜色扫描完毕
                p_x = x
                p_y = y
            elif (chk0 < 2 and chk1 < 2 and chk2 < 2) and p_x:
                # 圆柱狀目标块的顶层颜色不止一个像素, 需要定位中心点
                p_x = (x + p_x) // 2
                p_y = y
                break
        if p_x:
            break

    # 利用棋子落在中心点, 下一目标块中心点会有提示的特点, 快速定位落点
    # 如果没有中心点提示或者目标块是长方体则默认下移100像素
    zx = 0
    for y in range(p_y, p_y + 150):
        pixel = im_pixel[p_x, y]
        # 中心点颜色
        if pixel[0] == 254 and pixel[1] == 254 and pixel[2] == 254:
            p_y = y + 10
            print("找到目标位置Y坐标:", p_y)
            zx = 1
            break
    if zx == 0:
        p_y = p_y + 100

    print("dst position:", p_x, p_y)

    distance = math.sqrt((b_x - p_x) ** 2 + (b_y - p_y) ** 2)
    print(">>>> distance=", distance)
    return distance


def jump(distance):
    press_time = distance * press_coefficient
    press_time = max(press_time, 200)  # 设置 200ms 是最小的按压时间
    press_time = int(press_time)
    cmd = 'adb shell input swipe {x1} {y1} {x2} {y2} {duration}'.format(
        x1=200,
        y1=200,
        x2=200,
        y2=200,
        duration=press_time
    )
    os.system(cmd)

def main():
    op = yes_or_no('请确保手机打开了 ADB 并连接了电脑，' '然后打开跳一跳并【开始游戏】后再用本程序，确定开始？')
    debug.dump_device_info()
    screenshot.check_screenshot()

    i, next_rest, next_rest_time = (0, random.randrange(3, 10), random.randrange(5, 10))
    while True:
        # 截取图片
        screenshot.pull_screenshot()

        im = Image.open('./autojump.png')
        # 获取距离
        distance = find_piece_and_board(im)
        #distance = input("please input distance:")
        jump(int(distance))

        i += 1
        if i == next_rest:
            print('已经连续打了 {} 下，休息 {}s'.format(i, next_rest_time))
            for j in range(next_rest_time):
                sys.stdout.write('\r程序将在 {}s 后继续'.format(next_rest_time - j))
                sys.stdout.flush()
                time.sleep(1)
            print('\n继续')
            i, next_rest, next_rest_time = (0, random.randrange(30, 100), random.randrange(10, 60))

        time.sleep(random.uniform(0.9, 1.2))

if __name__ == '__main__':
    main()
