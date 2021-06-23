# Copyright Australian Conservation Foundation. All rights reserved.
# Developed by Ewan Short 2021
# eshort0401@gmail.com, https://github.com/eshort0401
import re


def detect_map(page, re_pttns, im_ratio=0.6):
    page_area = page.MediaBox[2] * page.MediaBox[3]
    page_area = page_area / 72 / 72  # inches squared
    total_img_area = 0
    bboxes = [info['bbox'] for info in page.get_image_info()]
    bboxes = list(set(bboxes))
    for box in bboxes:
        img_area = (box[2] - box[0]) * (box[3] - box[1])
        img_area = img_area / 72 / 72  # inches squared
        total_img_area += img_area
    large_image = total_img_area > im_ratio * page_area
    text_matches = []
    text = page.getText().lower().strip()
    if text == '':
        has_text = False
        text_matches = [False] * len(re_pttns)
    else:
        has_text = True
        for pttn in re_pttns:
            if re.search(pttn, text):
                text_matches.append(True)
            else:
                text_matches.append(False)
    return large_image, has_text, text_matches
