import os
import sys
from datetime import datetime as Datetime
import gradio as gr
import json
import requests
import threading
import time
import hashlib
sys.path.append('./')
from oss_utils import *
from myconfigs import *
from cache_util import RedisCache


scale_depth = 0.7
scale_pose = 0.5

def md5_hash_file(filename):
    """Compute the MD5 hash of the contents of the given file."""
    # Create a new MD5 hash object
    md5_hash = hashlib.md5()
    # Open the file in binary mode and read chunks
    with open(filename, 'rb') as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            md5_hash.update(byte_block)
    # Return the hexadecimal digest of the hash
    return md5_hash.hexdigest()

def get_dirnames(filePath='', tail=".mp4", reserve_num=-1):
    if not os.path.isdir(filePath):
        return []
    if len(tail) <= 0:
        return []
    len_tail = len(tail)
    lists = os.listdir(filePath)
    file_list = []
    for i in range(len(lists)):
        cur_file = lists[i]
        # if os.path.isfile(cur_file): 
        if len(cur_file) > 4 and cur_file[-len_tail:] == tail:
            full_file_path = os.path.join(filePath, cur_file)
            file_list.append(full_file_path)
    sorted_list = sorted(file_list, key=lambda x: os.path.getctime(x))
    sorted_list = sorted_list[::-1]
    if reserve_num > 0:
        for i in range(len(sorted_list)):
            if i >= reserve_num:
                os.remove(sorted_list[i])
    return sorted_list



def sync_request_local(request_id, data):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        # "Authorization": APP_AUTH_TEXTURE,
        # "X-DashScope-Async": "enable",
        # "X-DashScope-DataInspection": "enable"
    }    
    url_create_task = 'http://0.0.0.0:8000/api'
    
    print(f"request_id: {request_id}, request type: video generation, json input: {data}")
    res_ = requests.post(url_create_task, data=data, headers=headers)
    res = json.loads(res_.content.decode())
    
    result_video_url = ''
    if res['header']['status_name'] == 'Success':
        result_video_url = res['payload']['output']['res_video_path']
        print(f"request_id: {request_id}, request type: video generation, retuen message: Succees, result: {result_video_url}")
    else:
        print(f"request_id: {request_id}, request type: video generation, retuen message: Faild, result: {result_video_url}")
    return result_video_url

def sync_request_translate_en2cn(request_id, data):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": EAS_AUTH_CARTOONRECOG,
        # "X-DashScope-Async": "enable",
        # "X-DashScope-DataInspection": "enable"
    }    
    url_create_task = 'http://1096433202046721.cn-shanghai.pai-eas.aliyuncs.com/api/predict/videogene_supp/api'
    
    print(f"[{request_id}], request type: translate en2cn, json input: {data}")
    res_ = requests.post(url_create_task, data=data, headers=headers)
    # print(res_)
    # print(res_.content)
    res = json.loads(res_.content.decode())
    
    translate_cn = ''
    if res['payload']['output']['error_message'] == 'Success':
        translate_cn = res['payload']['output']['key']
        # print(f"{request_id} translate_cn: {translate_cn}")
        print(f"[{request_id}], request type: translate en2cn, retuen message: Succees, result: {translate_cn}")
    else:
        print(f"[{request_id}], request type: translate en2cn, retuen message: Faild, result: {translate_cn}")
    return translate_cn


def async_request_and_query(request_id, data):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        # "Authorization": APP_AUTH_TEXTURE,
        # "X-DashScope-Async": "enable",
        # "X-DashScope-DataInspection": "enable"
    }
    
    # 1. async request
    url_create_task = 'http://dashscope-scheduler-perf.1656375133437235.cn-beijing.pai-eas.aliyuncs.com/api/v1/task/submit'
    print(f"request_id: {request_id}, request type: video generation, json input: {data}")
    res_ = requests.post(url_create_task, data=data, headers=headers)
    # print("res_=", res_)
    # print(res_.content)
    result_json = json.loads(res_.content.decode("utf-8"))
    
    # 2.async query
    is_running = True
    running_print_count = 0
    res_video_path = None
    while is_running:
        url_query = 'http://dashscope-scheduler-perf.1656375133437235.cn-beijing.pai-eas.aliyuncs.com/api/v1/task/query-result'
        res_ = requests.post(url_query, data=data, headers=headers)
        respose_code = res_.status_code
        if 200 == respose_code:
            res = json.loads(res_.content.decode())
            if "SUCCESS" == res['header']['task_status']:
                if 200 == res['payload']['output']['error_code']:
                    res_video_path = res['payload']['output']['res_video_path']
                    print(f"request_id: {request_id}, request type: video generation, retuen message: Succees, result: {res_video_path}")
                    break
                else:
                    print(f'request_id: {request_id}, request type: video generation, retuen message: Faild, result: {result_json}')
                    # raise gr.Error(f'algo error.')
                    break
            elif "RUNNING" == res['header']['task_status']:
                if running_print_count == 0:
                    print(f'request_id: {request_id}, request type: video generation, retuen message: running..., result: {result_json}')
                    running_print_count += 1
                time.sleep(1)
            elif "FAILED" == res['header']['task_status']:
                print(f'request_id: {request_id}, request type: video generation, retuen message: Faild, result: {result_json}')
                # raise gr.Error(f'query result faild.')
                break
            else:
                print(f'request_id: {request_id}, request type: video generation, retuen message: Faild, result: {result_json}')
                # raise gr.Error(f'query result faild.')
                break
        else:
            print(f'request_id: {request_id}: Fail to query task result: {res_.content}')
            # raise gr.Error("Fail to query task result.")
            break
    return res_video_path


def async_request_video_generation(request_id, data):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        # "Authorization": APP_AUTH_TEXTURE,
        # "X-DashScope-Async": "enable",
        # "X-DashScope-DataInspection": "enable"
    }
    
    # async request
    url_create_task = 'http://dashscope-scheduler-perf.1656375133437235.cn-beijing.pai-eas.aliyuncs.com/api/v1/task/submit'
    print(f"request_id: {request_id}, request type: video generation, json input: {data}")
    res_ = requests.post(url_create_task, data=data, headers=headers)
    # print("res_=", res_)
    # print(res_.content)
    # result_json = json.loads(res_.content.decode("utf-8"))

def async_query_video_generation(request_id, data):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        # "Authorization": APP_AUTH_TEXTURE,
        # "X-DashScope-Async": "enable",
        # "X-DashScope-DataInspection": "enable"
    }
    
    # async query
    is_running = True
    running_print_count = 0
    res_video_path = None
    while is_running:
        url_query = 'http://dashscope-scheduler-perf.1656375133437235.cn-beijing.pai-eas.aliyuncs.com/api/v1/task/query-result'
        res_ = requests.post(url_query, data=data, headers=headers)
        respose_code = res_.status_code
        if 200 == respose_code:
            res = json.loads(res_.content.decode())
            if "SUCCESS" == res['header']['task_status']:
                if 200 == res['payload']['output']['error_code']:
                    res_video_path = res['payload']['output']['res_video_path']
                    print(f"request_id: {request_id}, request type: video generation, retuen message: Succees, result: {res_video_path}")
                    break
                else:
                    print(f'request_id: {request_id}, request type: video generation, retuen message: Faild, result: {res}')
                    # raise gr.Error(f'algo error.')
                    break
            elif "RUNNING" == res['header']['task_status']:
                if running_print_count == 0:
                    print(f'request_id: {request_id}, request type: video generation, retuen message: running..., result: {res}')
                    running_print_count += 1
                time.sleep(1)
            elif "FAILED" == res['header']['task_status']:
                print(f'request_id: {request_id}, request type: video generation, retuen message: Faild, result: {res}')
                break
            else:
                print(f'request_id: {request_id}, request type: video generation, retuen message: Faild, result: {res}')
                break
        else:
            print(f'request_id: {request_id}: Fail to query task result: {res_.content}')
            # raise gr.Error("Fail to query task result.")
            break
    return res_video_path


def query_video_generation(request_id, data):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        # "Authorization": APP_AUTH_TEXTURE,
        # "X-DashScope-Async": "enable",
        # "X-DashScope-DataInspection": "enable"
    }
    
    # async query
    is_running = True
    running_print_count = 0
    res_video_path = None
    # while is_running:
    url_query = 'http://dashscope-scheduler-perf.1656375133437235.cn-beijing.pai-eas.aliyuncs.com/api/v1/task/query-result'
    res_ = requests.post(url_query, data=data, headers=headers)
    respose_code = res_.status_code
    res = json.loads(res_.content.decode())
    if 200 == respose_code:
        if "SUCCESS" == res['header']['task_status']:
            if 200 == res['payload']['output']['error_code']:
                res_video_path = res['payload']['output']['res_video_path']
                print(f"request_id: {request_id}, request type: video generation, retuen message: Succees, result: {res_video_path}")
                return "SUCCESS", res
            else:
                print(f'request_id: {request_id}, request type: video generation, retuen message: Faild, result: {res}')
                return "FAILED", res
        elif "RUNNING" == res['header']['task_status']:
            print(f'request_id: {request_id}, request type: video generation, retuen message: running..., result: {res}')
            return "RUNNING", res
        elif "FAILED" == res['header']['task_status']:
            print(f'request_id: {request_id}, request type: video generation, retuen message: Faild, result: {res}')
            return "FAILED", res
        else:
            print(f'request_id: {request_id}, request type: video generation, retuen message: Faild, result: {res}')
            return "FAILED", res
    else:
        print(f'request_id: {request_id}: Fail to query task result: {res_.content}')
        return "FAILED", res


def sync_request_prompt_caption(request_id, data):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": EAS_AUTH_PROMPT,
        # "X-DashScope-Async": "enable",
        # "X-DashScope-DataInspection": "enable"
    }    
    url_create_task = 'http://1096433202046721.cn-shanghai.pai-eas.aliyuncs.com/api/predict/videogene_supp_gu50/api'
    
    print(f"request_id: {request_id}, request type: prompt_caption, json input: {data}")
    res_ = requests.post(url_create_task, data=data, headers=headers)
    # print(res_)
    # print(res_.content)
    res = json.loads(res_.content.decode())
    
    prompt_caption = ''
    gender = ''
    if res['payload']['output']['error_message'] == 'Success':
        key = res['payload']['output']['key'] # {"gender":"female","prompt":"Asian woman, 25-35, long black hair, dark brown eyes, average height","style":""}
        gender = key['gender']
        prompt_caption = key['prompt']
        style = key['style']
        print(f"request_id: {request_id}, request type: prompt_caption, retuen message: Succees, result: {prompt_caption}")
    else:
        print(f"request_id: {request_id}, request type: prompt_caption, retuen message: Faild, result: {prompt_caption}")
    return prompt_caption, gender, style

import re
def extract_mp4_filename(input_string):
    # Regular expression pattern to match the file name
    pattern = r"template_\d+\.mp4"
    # Extract the MP4 file name
    match = re.search(pattern, input_string)
    if match:
        return match.group()
    else:
        return None  # or you could raise an exception or return an empty string


class HumanGenService:
    def __init__(self):
        self.oss_service = ossService()
        self.all_user_requests = {}
        self.all_requests = []
        self.all_requests_time = {} # dict: request_id, time
        self.lock = threading.Lock()

    def translate_en2cn(self, request_id, input_prompt):
        #--------------- translate service -----------------#
        translate_data = {}
        translate_data['header'] = {}
        translate_data['header']['request_id'] = request_id
        translate_data['header']['service_id'] = ''
        translate_data['header']['task_id'] = request_id
        translate_data['header']['attributes'] = {}
        translate_data['header']['attributes']['user_id'] = ''
        translate_data['payload'] = {}
        translate_data['payload']['input'] = {}
        translate_data['payload']['input']['work_type'] = 'translate_en2zh'
        translate_data['payload']['input']['key'] = input_prompt
        translate_data['payload']['parameters'] = {}
        translate_data = json.dumps(translate_data) # to string        
        # serving api
        # print("input_prompt: ", input_prompt)        
        translate_cn = sync_request_translate_en2cn(request_id=request_id, data=translate_data)
        # print("translate_cn: ", translate_cn)        
        #--------------- translate service -----------------#
        print(f'[{request_id}] - [HumanGen] - translate ok')
        return translate_cn

    def signed_oss_path_to_internal(self, signed_oss_path):
        sign_internal_oss_path = ''
        import re
        pattern = r"http.*\.aliyuncs.com"
        match = re.search(pattern, signed_oss_path)
        if match:
            oss_address0 = match.group() 
            oss_address1 = signed_oss_path[len(oss_address0):] 
            oss_endpoint_seg = oss_address0[:-len(".aliyuncs.com")]
            sign_internal_oss_path = oss_endpoint_seg + '-internal.aliyuncs.com' + oss_address1
        else:
            print(f'[{request_id}] - [HumanGen] - signed_oss_path_to_internal faild for {signed_oss_path}')
        return sign_internal_oss_path  
        

    def click_button_prompt(self, user_id, request_id, input_mode, ref_image_path, ref_video_path, input_prompt='', prompt_template='',model_id=False):
        cartoon_recog = 'realhuman'  # input infer mode id 'face' and 'clothes'
        if model_id is False:
            cartoon_recog = 'realhuman'
        elif model_id is True:
            cartoon_recog = 'cartoon'
        
        if input_mode == 'prompt_mode':
            return input_prompt
        if cartoon_recog == 'cartoon':
            return prompt_template
        
        print(f"request_id: {request_id}, input_mode: {input_mode}")
        print(f"request_id: {request_id}, cartoon_recog: {cartoon_recog}")
        print(f"request_id: {request_id}, ref_image_path: {ref_image_path}")
        print(f"request_id: {request_id}, ref_video_path: {ref_video_path}")

        if input_mode == 'template_mode' and cartoon_recog == 'realhuman' and (ref_video_path is None or ref_video_path == ''):
            print(f"request_id: {request_id}, No video input, prompt caption over")
            raise gr.Error("No video input!")
            # return "请输入视频!"
        
        ref_video_name = ''
        user_mode = -1
        if input_mode == 'template_mode':
            import re
            # pattern = r"template_\d+\.mp4"
            pattern = r"template_.*\.mp4"
            # Extract the MP4 file name
            match = re.search(pattern, ref_video_path)
            if match:
                ref_video_name = match.group()
                user_mode = 0 # mode 0: image + template video
            else:
                user_mode = 1 # mode 1: image + upload video
        if input_mode == 'prompt_mode':
            user_mode = 2 # mode 2: image + prompt
            
        if user_mode == 0 and cartoon_recog == 'realhuman':
            return prompt_template

        date_string = datetime.datetime.now().strftime('%Y-%m-%d')
        img1_oss_path = ''
        vid1_oss_path = ''
        try:
            if input_mode == 'template_mode' and cartoon_recog == 'realhuman':
                vid_file_name = os.path.basename(ref_video_path)
                vid_extension = os.path.splitext(vid_file_name)[1] # .mp4
                vid1_oss_path = self.oss_service.ObjectName + '/Service/' + date_string + '/' + user_id + '/' + request_id + '/' + "ref_video" + vid_extension
                is_success1, sign_vid_oss_path = self.oss_service.uploadOssFile(vid1_oss_path, ref_video_path)
                print(f"request_id: {request_id}, is_success1={is_success1}, sign_vid_oss_path={sign_vid_oss_path}")
        except Exception as e:
            print(f"request_id: {request_id}, oss upload error for input local image or video. ")
            raise gr.Error("oss upload error for input local image or video")

        #-----------------------------prompt caption-----------------------------#
        # print("sign_img_oss_path: ", sign_img_oss_path)
        # print("sign_img_oss_path1: ", sign_img_oss_path)
        prompt_caption_data = {}
        prompt_caption_data['header'] = {}
        prompt_caption_data['header']['request_id'] = request_id
        prompt_caption_data['header']['service_id'] = 'test123'
        prompt_caption_data['header']['task_id'] = request_id
        prompt_caption_data['header']['attributes'] = {}
        prompt_caption_data['header']['attributes']['user_id'] = 'wanx_lab'
        prompt_caption_data['payload'] = {}
        prompt_caption_data['payload']['input'] = {}
        prompt_caption_data['payload']['input']['work_type'] = 'prompt_caption'
        sign_vid_oss_path = self.signed_oss_path_to_internal(sign_vid_oss_path)
        print(f"request_id: {request_id}, video internal oss path for caption: {sign_vid_oss_path}")
        prompt_caption_data['payload']['input']['key'] = sign_vid_oss_path
        prompt_caption_data['payload']['parameters'] = {}
        prompt_caption_data['payload']['parameters']['input_type'] = 'reference_video' # id_image,cartoon_id_image,reference_video
        prompt_caption_data['payload']['parameters']['input_format'] = 'url' # url,oss_path
        prompt_caption_data = json.dumps(prompt_caption_data) # to string

        # serving api
        prompt_caption_en,__,__ = sync_request_prompt_caption(request_id=request_id, data=prompt_caption_data)
        print(f"request_id: {request_id}, prompt caption: {prompt_caption_en}")
        #-----------------------------prompt caption-----------------------------#
        return prompt_caption_en # prompt_caption_cn


    def template_video_2_prompt(self, ref_video_name):
        file_name = ref_video_name
        ref_ori_video_path = ref_video_name
        print("videl filename:%s" % ref_video_name)
        input_prompt = ""
        if file_name[:len('template_')] == 'template_':
            file_name = extract_mp4_filename(file_name)
            if file_name not in template_prompts:
                raise gr.Error("The input video is not a template!")
            input_prompt = template_prompts[file_name]    
        else:
            print("video file not found:%s" % ref_video_name)
        return input_prompt
    
    def click_button_func_async(self, user_id, request_id, input_mode, ref_image_path, ref_video_path, input_prompt='', prompt_template='',model_id=False):
        start_time = time.time()
        if is_wanx_platform:
            user_id = 'wanx_lab'
            request_id = get_random_string()
            print(f"request_id: {request_id}, generate user_id: {user_id} and request_id: {request_id}")
        if user_id is None or user_id == '':
            user_id = 'test_version_phone'
        if request_id is None or request_id == '':
            request_id = get_random_string()
        # key by: ref_video_name, digest(ref_image_path), prompt_template, input_prompt, 
        # scale_depth, scale_pose
        #print("ref_image_path:%s ref_video_path:%s" % (ref_image_path, ref_video_path) )
        cache_key = None
        # if ref_image_path and os.path.exists(ref_image_path):
        #     digest_ref_image = md5_hash_file(ref_image_path)
        #     if ref_video_path and os.path.exists(ref_video_path):
        #         ref_video_name = os.path.basename(ref_video_path)
        #         cache_key = "%s_%s_%s_%s_%s_%s" % (ref_video_name, digest_ref_image, prompt_template, input_prompt, scale_depth, scale_pose)
        #         print("cache key:%s" % cache_key)
        
        # relative_oss_path = self.generate_video(cache_key, user_id, request_id, input_mode, ref_image_path, ref_video_path, input_prompt, prompt_template, model_id=model_id)
        self.generate_video(cache_key, user_id, request_id, input_mode, ref_image_path, ref_video_path, input_prompt, prompt_template, model_id=model_id)
        
        # oss_path = "oss://vigen-invi/" + relative_oss_path
        # style = "video/snapshot,t_1000,f_jpg,w_544,h_768,m_fast"
        # params = {'x-oss-process': style}
        # _, snapshot_image = self.oss_service.sign(oss_path, timeout=3600*100, params=params)
        # _, video_url = self.oss_service.sign(oss_path, timeout=3600*100)
        
        total_time_minutes = (time.time() -start_time) / 60  # minites
        print(f"request_id: {request_id}, Total process time: {total_time_minutes:.1f} minutes")
        
        # return video_url, snapshot_image
    
    #@RedisCache(expire=60*60*24*7) # 7 days
    def generate_video(self, cache_key, user_id, request_id, input_mode, ref_image_path, ref_video_path, input_prompt='', prompt_template='',model_id=False):
        self.lock.acquire()
        if user_id in self.all_user_requests and len(self.all_user_requests[user_id]) > 0:
            print(f"request_id: {request_id}, You still have unfinished tasks!")
            self.lock.release()
            raise gr.Error("You still have unfinished tasks!")
            # return None
        self.all_requests.append(request_id)
        if request_id not in self.all_requests_time:
            self.all_requests_time[request_id] = time.time()
        if user_id not in self.all_user_requests:
            self.all_user_requests[user_id] = []
            self.all_user_requests[user_id].append(request_id)
        else:
            self.all_user_requests[user_id].append(request_id)
        self.lock.release() 
        
        print(f">>>request_id: {request_id}, user_id: {user_id}, add a new task.")
        
        print(f"request_id: {request_id}, start process")

        ref_video_name = ''
        user_mode = -1
        if input_mode == 'template_mode':
            import re
            # pattern = r"template_\d+\.mp4"
            pattern = r"template_.*\.mp4"
            # Extract the MP4 file name
            match = re.search(pattern, ref_video_path)
            if match:
                ref_video_name = match.group()
                user_mode = 0 # mode 0: image + template video
            else:
                user_mode = 1 # mode 1: image + upload video
        if input_mode == 'prompt_mode':
            user_mode = 2 # mode 2: image + prompt

        cartoon_recog = 'realhuman'  # input infer mode id 'face' and 'clothes'
        if model_id is False:
            cartoon_recog = 'realhuman'
        elif model_id is True:
            cartoon_recog = 'cartoon'
       
        # try:
        #     import shutil
        #     dir_path = "/tmp/gradio"
        #     shutil.rmtree(dir_path)
        #     print(f"目录: {dir_path} 删除成功")
        # except OSError as e:
        #     print(f"目录: {dir_path} 删除失败:", e)

        date_string = datetime.datetime.now().strftime('%Y-%m-%d')
        img1_oss_path = ''
        vid1_oss_path = ''
        try:
            # ref image
            img_file_name = os.path.basename(ref_image_path)
            img_extension = os.path.splitext(img_file_name)[1] # 输出：.jpg
            img1_oss_path = self.oss_service.ObjectName + '/Service/' + date_string + '/' + user_id + '/' + request_id + '/' + "ref_image" + img_extension
            is_success0, sign_img_oss_path = self.oss_service.uploadOssFile(img1_oss_path, ref_image_path)
            print(f"request_id: {request_id}, is_success0={is_success0}, sign_img_oss_path={sign_img_oss_path}")

            if user_mode == 0 or user_mode == 1:
                vid_file_name = os.path.basename(ref_video_path)
                vid_extension = os.path.splitext(vid_file_name)[1] # 输出：.mp4
                vid1_oss_path = self.oss_service.ObjectName + '/Service/' + date_string + '/' + user_id + '/' + request_id + '/' + "ref_video" + vid_extension
                is_success1, sign_vid_oss_path = self.oss_service.uploadOssFile(vid1_oss_path, ref_video_path)
                print(f"request_id: {request_id}, is_success1={is_success1}, sign_vid_oss_path={sign_vid_oss_path}")
        except Exception as e:
            print(f"request_id: {request_id}, Data upload faild!")
            raise gr.Error("Data upload faild!")
            # return None
        
        #-----------------------------motion generation-----------------------------#
        data = '{"header":{"request_id":"","service_id":"","task_id":""},"payload":{"input": {"ref_image_path": "", "ref_video_path": "", "ref_video_name": "", "input_prompt": "", "prompt_template": "", "scale_depth": 0.7, "scale_pose": 0.5},"parameters":{}}}'
        data = json.loads(data) # string to dict
        data['header']['service_id'] = DASHONE_SERVICE_ID
        data['header']['request_id'] = request_id
        data['header']['task_id'] = request_id
        data['header']['attributes'] = {}
        data['header']['attributes']['user_id'] = user_id
        data['payload']['input']['user_id'] = user_id 
        data['payload']['input']['ref_image_path'] = img1_oss_path # sign_img_oss_path
        data['payload']['input']['ref_video_path'] = vid1_oss_path # sign_vid_oss_path
        data['payload']['input']['ref_video_name'] = ref_video_name
        data['payload']['input']['input_prompt'] = input_prompt
        data['payload']['input']['prompt_template'] = prompt_template
        data['payload']['input']['scale_depth'] = scale_depth
        data['payload']['input']['scale_pose'] = scale_pose
        data['payload']['input']['cartoon_recog'] = cartoon_recog
        data = json.dumps(data) # to string
        
        # serving api
        # sign_oss_path = sync_request_local(request_id=request_id, data=data) # sync
        
        try:
            async_request_video_generation(request_id=request_id, data=data) # async
            print(f"request_id: {request_id}, async_request_video_generation")
        except Exception as e:
            print(f"request_id: {request_id}, The video generation task has failed, possibly due to a server connection issue, please try again.")
            raise gr.Error("The video generation task has failed, possibly due to a server connection issue, please try again.")
            # return None
        
        print(f"=================end request_id: {request_id}")
        # return sign_oss_path


    def valid_check(self, user_id, request_id, input_mode, ref_image_path, ref_video_path, input_prompt='', prompt_template='',model_id=False):
        if is_wanx_platform:
            user_id = 'wanx_lab'
        if user_id is None or user_id == '':
            user_id = 'test_version_phone'
        if request_id is None or request_id == '':
            request_id = get_random_string()
        print(f"-----------------request_id: {request_id}, user_id: {user_id}---------------")
        
        self.lock.acquire()
        if user_id in self.all_user_requests:
            if len(self.all_user_requests[user_id]) > 0:
                self.lock.release()
                # raise gr.Error("Your video is in the process of being generated. Please wait until the process is complete before submitting a new task. Click refresh to get the latest progress updates.")
                return "Your video is in the process of being generated. Please wait until the process is complete before submitting a new task. Click refresh to get the latest progress updates."
        self.lock.release()
        
        cartoon_recog = 'realhuman'  # input infer mode id 'face' and 'clothes'
        if model_id is False:
            cartoon_recog = 'realhuman'
        elif model_id is True:
            cartoon_recog = 'cartoon'
        
        print(f"request_id: {request_id}, input_mode: {input_mode}")
        print(f"request_id: {request_id}, ref_image_path: {ref_image_path}")
        print(f"request_id: {request_id}, ref_video_path: {ref_video_path}")
        print(f"request_id: {request_id}, input_prompt = {input_prompt}")
        print(f"request_id: {request_id}, prompt_template = {prompt_template}")
        print(f"request_id: {request_id}, scale_depth = {scale_depth}")
        print(f"request_id: {request_id}, scale_pose = {scale_pose}")
        print(f"request_id: {request_id}, model_id = {model_id}")
        print(f"request_id: {request_id}, style: {cartoon_recog}")

        if ref_image_path is None or ref_image_path == '' or (not os.path.exists(ref_image_path)):
            print(f"request_id: {request_id}, No image input, task over!")
            # raise gr.Error("请输入图片!")
            return "Please input a image."
        
        if input_mode == 'template_mode' and cartoon_recog == 'realhuman' and (prompt_template == '' or prompt_template == [] or prompt_template is None):
            print(f"request_id: {request_id}, No prompt input, task over!")
            # raise gr.Error("请输入prompt!")
            return "Please input a prompt."
        
        if input_mode == 'prompt_mode' and cartoon_recog == 'realhuman' and (input_prompt == '' or input_prompt == [] or input_prompt is None):
            print(f"request_id: {request_id}, No prompt input, task over!")
            # raise gr.Error("请输入prompt!")
            return "Please input a prompt."
        
        if input_mode == 'template_mode' and (ref_video_path is None or ref_video_path == ''):
            print(f"request_id: {request_id}, No video input, task over!")
            # raise gr.Error("请输入视频!")
            return "Please input a video."
        
        ref_video_name = ''
        user_mode = -1
        if input_mode == 'template_mode':
            import re
            # pattern = r"template_\d+\.mp4"
            pattern = r"template_.*\.mp4"
            # Extract the MP4 file name
            match = re.search(pattern, ref_video_path)
            if match:
                ref_video_name = match.group()
                user_mode = 0 # mode 0: image + template video
            else:
                user_mode = 1 # mode 1: image + upload video
        if input_mode == 'prompt_mode':
            user_mode = 2 # mode 2: image + prompt
        print(f"request_id: {request_id}, user_mode = {user_mode} (0: image + template video, 1: image + upload video, 2: image + prompt)")
        
        return ''

    def delete_request_id(self, user_id, request_id, lock=True):
        if lock:
            self.lock.acquire()
        if request_id in self.all_requests:
            self.all_requests.remove(request_id)
        if user_id in self.all_user_requests and request_id in self.all_user_requests[user_id]:
            self.all_user_requests[user_id].remove(request_id)
        if request_id in self.all_requests_time:
            del self.all_requests_time[request_id] 
        if lock:
            self.lock.release()

    def get_ranking_location(self, user_id):
        if is_wanx_platform:
            user_id = 'wanx_lab'
        if user_id is None or user_id == '':
            user_id = 'test_version_phone'
        process_status = ''
        
        if len(self.all_requests) > 0:
            for i in range(min(num_instance_dashone, len(self.all_requests))):
                req = self.all_requests[i]
                waste_time = 10000
                if req in self.all_requests_time:
                    endt = time.time()
                    startt = self.all_requests_time[req]
                    waste_time = (endt - startt)/60
                if waste_time > avg_process_time + 1:
                    data = '{"header":{"request_id":"","service_id":"","task_id":""},"payload":{"input": {"ref_image_path": "", "ref_video_path": "", "ref_video_name": "", "input_prompt": "", "prompt_template": "", "scale_depth": 0.7, "scale_pose": 0.5},"parameters":{}}}'
                    data = json.loads(data) # string to dict
                    data['header']['service_id'] = DASHONE_SERVICE_ID
                    data['header']['request_id'] = req
                    data['header']['task_id'] = req
                    data['header']['attributes'] = {}
                    data['header']['attributes']['user_id'] = user_id
                    data['payload']['input']['user_id'] = user_id 
                    data = json.dumps(data) # to string                
                    ret_status, ret_json = query_video_generation(request_id=req, data=data)
                    # print(f'ret_json = {ret_json}')  
                    if ret_status == "SUCCESS" or ret_status == "FAILED":
                        if req in self.all_requests:
                            self.all_requests.remove(req) # delete request_id
                        if req in self.all_requests_time:
                            del self.all_requests_time[req] 
                    else:
                        break
                else:
                    break
        else:
            print(f'size of all_requests is empty.')
        
        if user_id not in self.all_user_requests:
            return f'You have not request a video generation task.', ''
        
        if len(self.all_user_requests[user_id]) == 0:
            return f'You do not have any tasks in progress, queue status.:{len(self.all_requests)}', ''
        else:
            self.lock.acquire()
            lenn = len(self.all_user_requests[user_id])
            if lenn > 1:
                for j in range(lenn - 1):
                    req = self.all_user_requests[user_id][j]
                    self.delete_request_id(user_id, req, lock=False) # delete request_id
            request_id = self.all_user_requests[user_id][0]
            self.lock.release()
            
            data = '{"header":{"request_id":"","service_id":"","task_id":""},"payload":{"input": {"ref_image_path": "", "ref_video_path": "", "ref_video_name": "", "input_prompt": "", "prompt_template": "", "scale_depth": 0.7, "scale_pose": 0.5},"parameters":{}}}'
            data = json.loads(data) # string to dict
            data['header']['service_id'] = DASHONE_SERVICE_ID
            data['header']['request_id'] = request_id
            data['header']['task_id'] = request_id
            data['header']['attributes'] = {}
            data['header']['attributes']['user_id'] = user_id
            data['payload']['input']['user_id'] = user_id 
            data = json.dumps(data) # to string                
            ret_status, ret_json = query_video_generation(request_id=request_id, data=data)
            print(f'ret_json = {ret_json}')
            if ret_status == "SUCCESS":
                req = self.all_user_requests[user_id][0]
                self.delete_request_id(user_id, req) # delete request_id
                return 'Your video has been successfully generated.', ''
            elif ret_status == "FAILED":
                req = self.all_user_requests[user_id][0]
                self.delete_request_id(user_id, req) # delete request_id           
                # if ret_json['header']['status_code'] == 200:
                #     if ret_json['header']['status_code'][]
                return 'Your video generation failed, you may try enabling the "Cartoon Video Generation" option.', ''
            else:
                process_status = 'runing'
                self.lock.acquire()
                tmp_all_requests = self.all_requests.copy()
                tmp_all_requests_time = self.all_requests_time.copy()
                self.lock.release()
                for i in range(len(tmp_all_requests)):
                    if tmp_all_requests[i] == request_id:
                        index = i + 1
                        endt = time.time()
                        rest_time_list = []
                        for k in range(i+1):
                            reqestid = tmp_all_requests[k]
                            startt = tmp_all_requests_time[reqestid] 
                            wast_time = endt-startt 
                            rest_time = max(0, avg_process_time * 60 - wast_time)
                            rest_time_list.append(rest_time)
                        sorted_time = sorted(rest_time_list, reverse=False)
                        
                        print(f'rest_time_list: {rest_time_list}')
                        print(f'sorted_time: {sorted_time}')
                            
                        process_time = 0
                        if index <= num_instance_dashone:
                            process_time = rest_time_list[i]/60
                            return f'Your video generation task is being processed, please wait for about {process_time:.1f} minutes, click refresh to get the latest progress update.', process_status
                        else:
                            rounds_to_wait = index // num_instance_dashone
                            rounds_to_rest = index % num_instance_dashone - 1
                            process_time = rounds_to_wait * avg_process_time + sorted_time[rounds_to_rest]/60
                            return f'There are {index-1} tasks ahead of you in the queue, please wait for about {process_time:.1f} minutes, click refresh to get the latest progress update.', process_status
                return f'You do not have any tasks currently being processed.', process_status
                     
