from pydub import AudioSegment
from pydub.playback import *
from math import sqrt, e, log
import moviepy.editor as mpe
import librosa
import numpy as np
import cv2
import os
import random
import copy


def add_to_master(master, segment, position):
    # If adding the segment increases the length of master, allocate the silence needed
    if len(segment) + position > len(master):
        master = master + AudioSegment.silent((len(segment) + position) - len(master))

    # Overlay the segment on master
    master = master.overlay(segment, position=position)

    # Returns the current position
    return master, len(segment) + position


def fib(n):
    return int(((1 + sqrt(5)) ** n - (1 - sqrt(5)) ** n) / (2 ** n * sqrt(5)))


def render_audio():
    master = AudioSegment.silent(0)
    dubois = AudioSegment.from_file("dubois.mp3")[2400:].fade_in(10)
    air = dubois[40800:40800 + 1000]

    pos = 0

    # Add opening phrase
    open_phrase_end = 7400
    master, pos = add_to_master(master, dubois[:open_phrase_end], pos)
    master, pos = add_to_master(master, dubois[1925:1925 + 2475].fade_in(10).fade_out(10), pos)
    master, pos = add_to_master(master, dubois[500:500 + 1220].fade_in(10).fade_out(10), pos)
    master, pos = add_to_master(master, dubois[8500:8500 + 640].fade_in(10).fade_out(10), pos)
    master, pos = add_to_master(master, dubois[13800:13800 + 3650].fade_in(10).fade_out(10), pos)
    master, pos = add_to_master(master, dubois[31400:31400 + 3280].fade_in(10).fade_out(10), pos)
    master, pos = add_to_master(master, air[:800].fade_in(10).fade_out(10), pos)
    master, pos = add_to_master(master, dubois[500:1750].fade_in(40).fade_out(150), pos)
    master, pos = add_to_master(master, air[:800].fade_in(10).fade_out(10) * 3, pos)
    master, pos = add_to_master(master, dubois[500:1750].fade_in(40).fade_out(150), pos)
    master, pos = add_to_master(master, dubois[69600:69600 + 150].fade_out(10) * 8, pos)

    proc_start = 69600
    regions = 48
    region_len = int(len(dubois[proc_start:]) // regions)

    for r in range(regions):
        region_start = proc_start + (r * region_len)
        region_end = region_start + region_len

        switch = random.choice([True, False, False, False, False])

        if r == (regions - 1):
            switch = True

        if switch:
            # Long
            length = int(2000 + (1000 * random.random()))
            num_times = 1
        else:
            # Short
            length = int(100 + (500 * random.random()))
            num_times = random.choice([2, 3, 4, 5])

        for _ in range(num_times):
            start = np.random.randint(region_start, region_end - length)
            master, pos = add_to_master(master, dubois[start:start + length], pos)


    print("Saving remix.")
    master.export("master.mp3", format="mp3")


def make_video():
    print("Loading remix.")
    samples, sr = librosa.core.load("master.mp3")
    num_samples = len(samples)
    time_in_seconds = num_samples / sr
    video_frame_rate = 60

    samples_per_frame = int(num_samples // (time_in_seconds * video_frame_rate))

    writer = cv2.VideoWriter('video.mp4', cv2.VideoWriter_fourcc(*'mp4v'), video_frame_rate, (640, 480))
    dubois_image = cv2.imread("doobwa.png")

    i = 0
    j = 0
    while i < num_samples:
        if i + samples_per_frame < num_samples:
            blk = samples[i:i + samples_per_frame]
        else:
            blk = samples[i:]

        frame = copy.copy(dubois_image).astype('uint8')

        mag = np.average(librosa.feature.rmse(blk, frame_length=len(blk))) * 10
        feat = np.average(librosa.feature.spectral_centroid(blk, sr=sr))
        if feat != 0:
            feat = log(feat)

        axis = random.choice([0, 1])
        dir = random.choice([-1, 1])

        for _ in range(int(feat * 3) * (2 + int(10 * (mag - 0.2)))):
            x = np.random.randint(0, frame.shape[0])
            y = np.random.randint(0, frame.shape[1])
            if axis == 0:
                frame[:, y, :] = np.roll(frame[:, y, :], int(mag * feat) * 100 * dir)
            else:
                frame[x, :, :] = np.roll(frame[x, :, :], int(mag * feat) * 100 * dir)

        writer.write(frame)
        i += samples_per_frame
        j += 1
        print("Frame %d/%d." % (j, int(time_in_seconds * video_frame_rate)))


def set_audio_to_video():
    my_clip = mpe.VideoFileClip('video.mp4')
    audio_background = mpe.AudioFileClip('master.mp3')
    final_clip = my_clip.set_audio(audio_background)
    try:
        os.remove("out.mp4")
    except:
        pass
    final_clip.write_videofile("out.mp4")


if __name__ == "__main__":
    # render_audio()
    # make_video()
    set_audio_to_video()
    print("Done")
