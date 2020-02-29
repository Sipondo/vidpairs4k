from __future__ import unicode_literals
import csv
import os
import re
import shutil
import subprocess
import youtube_dl
import time

formats = [3840, 2160, 1080, 720, 500]

ydl_opts = {
    'format': '313',
    'outtmpl': 'tempvideo/trailer.webm',
 }

paths = ['dataset', 'tempvideo', 'tempimages'] + [f'dataset/{format}' for format in formats]

# paths = ['tempvideo', 'tempimages']

for path in paths:
    try:
        shutil.rmtree(path)
    except OSError:
        print ("Removing of the directory %s failed" % path)
    else:
        print ("Successfully removed the directory %s " % path)
    time.sleep(0.1)
    try:
        os.mkdir(path)
    except OSError:
        print ("Creation of the directory %s failed" % path)
    else:
        print ("Successfully created the directory %s " % path)

def grouped(iterable, n):
    "s -> (s0,s1,s2,...sn-1), (sn,sn+1,sn+2,...s2n-1), (s2n,s2n+1,s2n+2,...s3n-1), ..."
    return zip(*[iter(iterable)]*n)

class MyLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        print(msg)


def my_hook(d):
    if d['status'] == 'finished':
        print('Done downloading, now converting ...')




def load_urls():
    with open("dataset.csv") as file:
        reader = csv.reader(file)
        return [row for row in reader]

def download_video(url):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def ffmpeg_get_crop():
    res = str(subprocess.check_output("ffmpeg -ss 15 -i tempvideo/trailer.webm -vframes 300 -vf cropdetect -f null -",  stderr=subprocess.STDOUT))
    res = res.split("crop=3840:")[1]
    offset = res.split(":0:")[1][:3]
    offset = re.sub('[^0-9]','', offset)
    res = re.sub('[^0-9]','', res[:4])
    return res, offset#subprocess.call(f"ffmpeg -loglevel quiet -i tempvideo/trailer.webm -vf crop=3840:{res[:4]}:0:0 -c:a copy tempvideo/trailerclean.webm")

def ffmpeg_apply_crop(target, dest, res, offset):
    subprocess.call(f"ffmpeg -loglevel quiet -y -i {target} -vf crop=3840:{res}:0:{offset} {dest}")

def ffmpeg_keysplit():
    subprocess.call("ffmpeg -loglevel quiet -y -i tempvideo/trailer.webm -an -f segment -vcodec copy -reset_timestamps 1 -map 0 tempvideo/OUTPUT%d.mp4")

def ffmpeg_split_into_images(target):
    subprocess.call(f"ffmpeg -loglevel quiet -y -i {target} tempimages/thumb%04d.jpg -hide_banner")

def ffmpeg_copy_to_lower_res(target, res):
    for format in formats[1:]:
        scale = formats[0]/format
        subprocess.call(f"ffmpeg -loglevel quiet -y -i dataset/{formats[0]}/{target} -vf scale={format}:{int(res)/scale} dataset/{format}/{target}")


url_list = load_urls()



current_image = 0
last_line = ""
current_downloaded = ""
for download_line in url_list:
    need_to_run = False
    for frame, start, length in grouped(download_line[1:], 3):
        all_present = True
        for format in formats[:]:
            all_present = all_present and (os.path.isfile(f'dataset/{format}/{current_image}.jpg'))
            all_present = all_present and (os.path.isfile(f'dataset/{format}/{current_image+1}.jpg'))
        need_to_run = need_to_run or (not all_present)

    if download_line[0]!='*':
        last_line = download_line[0]
    if need_to_run:
        if (last_line == current_downloaded):
            pass
        else:
            current_downloaded = last_line
            shutil.rmtree('tempvideo/')
            time.sleep(1)
            os.mkdir('tempvideo/')

            print("Video: ", last_line, current_image, ((current_image+2)//2))
            download_video(last_line)
            crop_res, crop_offset = ffmpeg_get_crop()
            ffmpeg_keysplit()

        for frame, start, length in grouped(download_line[1:], 3):
            print(current_image, "Instruction:", current_image//2+1, frame, start, length)
            frame = int(frame)
            start = int(start)
            length = int(length)
            # print("Splitting", f"tempvideo/OUTPUT{frame}.mp4")

            shutil.rmtree('tempimages/')
            time.sleep(1)
            os.mkdir('tempimages/')
            ffmpeg_split_into_images(f"tempvideo/OUTPUT{frame}.mp4")
            ffmpeg_apply_crop(f'tempimages/thumb{start:04}.jpg', f'dataset/3840/{current_image}.jpg', crop_res, crop_offset)
            ffmpeg_copy_to_lower_res(f'{current_image}.jpg', crop_res)
            current_image+=1
            ffmpeg_apply_crop(f'tempimages/thumb{start+length:04}.jpg', f'dataset/3840/{current_image}.jpg', crop_res, crop_offset)
            ffmpeg_copy_to_lower_res(f'{current_image}.jpg', crop_res)
            current_image+=1

        all_present = True
        for format in formats[:]:
            all_present = all_present and (os.path.isfile(f'dataset/{format}/{current_image-1}.jpg'))
            all_present = all_present and (os.path.isfile(f'dataset/{format}/{current_image-2}.jpg'))
        if not all_present:
            exit[0]
    else:
        print(f"Skipping {current_image} ({(current_image+2)//2})")
        for frame, start, length in grouped(download_line[1:], 3):
            current_image+=2
