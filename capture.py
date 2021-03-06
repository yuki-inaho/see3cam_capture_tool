import sys
import cv2
import click
import numpy as np
import os
import cvui
import toml
import shutil
import glob
import pdb
import time

from pytz import timezone
from datetime import datetime
from scripts.rgb_manager import RgbCameraManager
from scripts.camera_parameter import IntrinsicParam
from scripts.lens_undistortion import LensUndistorter
from functools import partial

#    now = datetime.datetime.today()
#    date = str(now.year) + "-" + str(now.month) + "-" + str(now.day) + "-" + str(now.hour) + ":" + str(now.minute) + ":" + str(now.second)
#    print(date)
#    dir_name = os.path.join(dir_name, date)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def is_wdr_enabled(camera_name, cfg_path):
    toml_dict = toml.load(open(cfg_path))
    isWDR = int(toml_dict[camera_name]["range1"]) >= 0 and int(toml_dict[camera_name]["range2"]) >= 0
    isRGB = int(toml_dict[camera_name]["rgb_image"]) == 1
    do_exit = False
    if not isWDR:
        print("Current camera setting is WDR disabled mode. This app can be executed under WDR enabled setting")
        do_exit = True
    if isRGB:
        print("Current camera setting is RGB enabled mode. This app can be executed under RGB disabled setting")
        do_exit = True
    if do_exit:
        assert False


def get_time():
    utc_now = datetime.now(timezone("UTC"))
    jst_now = utc_now.astimezone(timezone("Asia/Tokyo"))
    time = str(jst_now).split(".")[0].split(" ")[0] + "_" + str(jst_now).split(".")[0].split(" ")[1]
    return time


def make_save_dir(save_dir_path):
    if not os.path.exists(save_dir_path):
        os.mkdir(save_dir_path)


def clean_save_dir(save_dir_path):
    if os.path.exists(save_dir_path):
        shutil.rmtree(save_dir_path)
    os.mkdir(save_dir_path)


def save_image(see3cam_rgb_img, save_dir):
    time = get_time()
    cv2.imwrite(os.path.join(save_dir, "{}.png".format(time)), see3cam_rgb_img)
    cv2.waitKey(10)


def scaling_int(int_num, scale):
    return int(int_num * scale)


@click.command()
@click.option("--toml-path", "-t", default="{}/cfg/camera_parameter.toml".format(SCRIPT_DIR))
@click.option("--directory-for-save", "-s", default="{}/data".format(SCRIPT_DIR))
@click.option("--save-raw-data", "-raw", is_flag=True)
@click.option("--scale", "-sc", default=0.75)
@click.option("--timelapse-mode", "-lapse", is_flag=True)
@click.option("--interval-minute", "-i", default=5)
def main(toml_path, directory_for_save, save_raw_data, scale, timelapse_mode, interval_minute):
    make_save_dir(directory_for_save)
    see3cam_mng = RgbCameraManager(toml_path)
    lens_undistorter = LensUndistorter(toml_path)
    scaling = partial(scaling_int, scale=scale)

    WINDOW_NAME = "Capture"
    cvui.init(WINDOW_NAME)
    while True:
        key = cv2.waitKey(10)
        frame = np.zeros((scaling(960), scaling(1400), 3), np.uint8)
        frame[:] = (49, 52, 49)

        status = see3cam_mng.update()

        number_of_saved_frame = len(glob.glob(os.path.join(directory_for_save, "*.png")))
        cvui.printf(frame, 50, scaling(750), 0.8, 0x00FF00, "Number of Captured Images : %d", number_of_saved_frame)

        if status:
            see3cam_rgb_image_raw = see3cam_mng.read()
            see3cam_rgb_image_undist = lens_undistorter.correction(see3cam_rgb_image_raw)
            scaled_width = scaling(1280)
            scaled_height = scaling(720)
            see3cam_rgb_resize = cv2.resize(see3cam_rgb_image_undist, (scaled_width, scaled_height))

            cvui.text(frame, 10, 10, "See3CAM", 0.5)
            frame[10 : scaled_height + 10, 10 : scaled_width + 10, :] = see3cam_rgb_resize

            # For time lapse capturing
            capture_condition = cvui.button(frame, 50, scaling(800), 200, 100, "capture image") or key & 0xFF == ord("s")
            if timelapse_mode:
                current_time = datetime.now()
                if  current_time.minute % interval_minute == 0 and current_time.second % 60 == 0:
                    print("captured:{}, time:{}".format(number_of_saved_frame, current_time))
                    capture_condition = True

            if capture_condition:
                if status:
                    if save_raw_data:
                        save_image(see3cam_rgb_image_raw, directory_for_save)
                    else:
                        save_image(see3cam_rgb_image_undist, directory_for_save)

            if timelapse_mode:
                time.sleep(1)

            if cvui.button(frame, 300, scaling(800), 200, 100, "erase"):
                clean_save_dir(directory_for_save)

        if key == 27 or key == ord("q"):
            break

        cvui.update()
        cvui.imshow(WINDOW_NAME, frame)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
