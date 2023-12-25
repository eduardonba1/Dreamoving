# -*- coding: utf-8 -*-
import os
import sys
import string
import time
import datetime
import json
from io import BytesIO
import oss2
import random
import requests
import shutil
from myconfigs import *

use_internal_network = False

def get_random_string():
    now = datetime.datetime.now()
    date = now.strftime('%Y%m%d')
    time = now.strftime('%H%M%S')
    microsecond = now.strftime('%f')
    microsecond = microsecond[:6] 

    rand_num = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    random_string = ''.join(random.choices(string.ascii_uppercase, k=6)) # ascii_lowercase
    return date + "-" + time + "-" + microsecond + "-" + random_string

class ossService():
    def __init__(self):
        self.AccessKeyId = OSSAccessKeyId
        self.AccessKeySecret = OSSAccessKeySecret
        self.Endpoint = "https://oss-cn-shanghai.aliyuncs.com"
        if use_internal_network: 
            self.Endpoint = "https://oss-cn-shanghai-internal.aliyuncs.com"
        self.BucketName = "vigen-invi" # "vigen-video"
        self.ObjectName = "video_generation" # "VideoGeneration"
        self.Prefix = "oss://" + self.BucketName

        auth = oss2.Auth(self.AccessKeyId, self.AccessKeySecret)
        self.bucket = oss2.Bucket(auth, self.Endpoint, self.BucketName)

    # oss_url: eg: oss://BucketName/ObjectName/xxx.mp4
    # timeout: eg: 3600*100
    # params: eg: {'x-oss-process': style}
    def sign(self, oss_url, timeout=3600, params=None):
        try:
            oss_path = oss_url[len("oss://" + self.BucketName + "/"):]
            return 1, self.bucket.sign_url('GET', oss_path, timeout, slash_safe=True, params=params)
        except Exception as e:
            print("sign error: {}".format(e))
            return 0, ""
        
    def uploadOssFile(self, oss_full_path, local_full_path):
        try:
            self.bucket.put_object_from_file(oss_full_path, local_full_path)
            return self.sign(self.Prefix+"/"+oss_full_path, timeout=3600)
        except oss2.exceptions.OssError as e:
            print("oss upload error: ", e)
            return 0, ""

    def downloadOssFile(self, oss_full_path, local_full_path):
        status = 1
        try:
            self.bucket.get_object_to_file(oss_full_path, local_full_path)
        except oss2.exceptions.OssError as e:
            print("oss download error: ", e)
            status = 0
        return status

        
    def downloadFile(self, file_full_url, local_full_path):
        status = 1
        response = requests.get(file_full_url)
        if response.status_code == 200:
            with open(local_full_path, "wb") as f:
                f.write(response.content)
        else:
            print("oss download error. ")
            status = 0
        return status
