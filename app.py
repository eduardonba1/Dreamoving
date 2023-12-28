import os
import time
import gradio as gr
import threading
from myconfigs import *
from oss_utils import ossService

from gen_client import *
myHumanGen = HumanGenService()
oss_service = ossService()

ENABLE_OSS_RESOURCES = False

# result_video_oss_url = {} # user_id, (list[signed_url), list[oss_path])]

def tab_func_template():
    prompt = ""
    return prompt, 'template_mode'
def tab_func_prompt():
    ref_video_path = None
    return ref_video_path, 'prompt_mode'
    
def video_2_prompt_func(ref_video_path):
    print("[dataset_func] ref_video_path: %s" % ref_video_path)
    if not os.path.exists(ref_video_path):
        raise gr.Error(f"The input video {ref_video_path} is not existed!")
    video_file_name = os.path.basename(ref_video_path)
    print("[dataset_func] video_file_name: %s" % video_file_name)
    input_prompt = myHumanGen.template_video_2_prompt(video_file_name)
    print("[dataset_func] input_prompt: %s" % input_prompt)
    return ref_video_path,input_prompt


def get_user_result_video_list(uuid, date_string, num):
    directory='video_generation/Service/'+date_string+'/'+uuid+'/'
    for obj in oss2.ObjectIterator(oss_service.bucket, prefix=directory, delimiter='/'):
        print(f"folder is existed{directory}")
        break
    else:
        print(f"folder is not existed: {directory}")
        return [],[]
    no_check_video_list = []
    no_check_timer_list = []
    for obj in oss2.ObjectIterator(oss_service.bucket, prefix=directory, delimiter = '/'):
        if obj.is_prefix():  # folder
            file_full_path = obj.key+'result.mp4'
            exist = oss_service.bucket.object_exists(file_full_path)
            
            if not exist:
                print(f'{file_full_path} is not existed')
                tmp_directory=obj.key
                print(f'tmp_directory = {tmp_directory}')
                for obj_xxx in oss2.ObjectIterator(oss_service.bucket, prefix=tmp_directory, delimiter = '/'):
                    print(f'obj_xxx.key = {obj_xxx.key}')
                    if obj_xxx.is_prefix():  # folder
                        pass
                    else:
                        import re
                        pattern = r"dreamoving-.*-result\.mp4"
                        # Extract the MP4 file name
                        file_name_xxx = os.path.basename(obj_xxx.key)
                        match = re.search(pattern, obj_xxx.key)
                        if match and len(match.group()) == len(file_name_xxx):
                            file_full_path = obj_xxx.key
                            print(f'successfully match file_full_path: {file_full_path}')
                            exist = True
                            break
            else:
                pass
                    
            if exist:
                object_meta = oss_service.bucket.head_object(file_full_path)
                bytes_num = object_meta.headers.get('Content-Length') # bytes
                # print(f"Object Size: {bytes_num} bytes")
                mb_num = float(bytes_num) / (1000 ** 2) # MB
                # print(f"Object Size: {mb_num} MB")

                if mb_num > 0.1: # > 100KB
                    last_modified = object_meta.headers.get('Last-Modified')
                    # print(f"Last Modified: {last_modified}")
                    from email.utils import parsedate_to_datetime
                    # HTTP-date to datetime 
                    last_modified_datetime = parsedate_to_datetime(last_modified)
                    # datetime to Unix Time -from 1970-01-01 UTC seconds, nearest is bigger
                    last_modified_timestamp = int(last_modified_datetime.timestamp())

                    no_check_video_list.append(file_full_path)
                    no_check_timer_list.append(last_modified_timestamp)
                else:
                    print(f'file size: {file_full_path}')       
        else:   # file
            print(f'not a file: {obj.key}') 
            # last_modified = obj.last_modified  # last modify time
        
    valid_video_list = []
    valid_image_list = []
    if len(no_check_video_list) > 0:
        if len(no_check_video_list) > 1:
            # sort by time
            zipped_lists = zip(no_check_timer_list, no_check_video_list) 
            # big to small, nearest is bigger
            sorted_pairs = sorted(zipped_lists, key=lambda x: x[0], reverse=True) 
            list1_sorted, list2_sorted = zip(*sorted_pairs)
            no_check_timer_list = list(list1_sorted)
            no_check_video_list = list(list2_sorted)
        
        for file_full_path in no_check_video_list:
            oss_video_path = oss_service.Prefix + "/" + file_full_path
            print(f'Generated video: {oss_video_path}')
            _, video_url = oss_service.sign(oss_video_path, timeout=3600*100)
            valid_video_list.append(video_url)
            style = "video/snapshot,t_1000,f_jpg,w_544,h_768,m_fast"
            params1 = {'x-oss-process': style}
            _, snapshot_image = oss_service.sign(oss_video_path, timeout=3600*100, params=params1)
            valid_image_list.append(snapshot_image)
            if len(valid_video_list) >= num:
                break
    return valid_video_list, valid_image_list

def refresh_video(uuid, request_id):
    notes, process_status = myHumanGen.get_ranking_location(uuid)
    if is_wanx_platform:
        uuid = 'wanx_lab'
    if uuid is None or uuid == '':
        uuid = 'test_version_phone'
    print(f'[refresh_video] uuid: {uuid}')
    print(f'[refresh_video] request_id: {request_id}')
    new_list = []
    new_image_list = []
    if process_status == 'runing':
        print(f'process_status: {process_status}')
        # new_list.append(None)
        # new_image_list.append(None)
        date_string = datetime.datetime.now().strftime('%Y-%m-%d')
        valid_video_list, valid_image_list = get_user_result_video_list(uuid, date_string, 3)
        new_list = new_list + valid_video_list
        new_image_list = new_image_list + valid_image_list
        if len(new_list) < 4:
            date_string_yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
            valid_video_list1, valid_image_list1 = get_user_result_video_list(uuid, date_string_yesterday, 4-len(new_list))
            new_list = new_list + valid_video_list1
            new_image_list = new_image_list + valid_image_list1
        if len(new_list) < 4:
            date_string_bf_yesterday = (datetime.datetime.now() - datetime.timedelta(days=2)).strftime('%Y-%m-%d')
            valid_video_list2, valid_image_list2 = get_user_result_video_list(uuid, date_string_bf_yesterday, 4-len(new_list))
            new_list = new_list + valid_video_list2
            new_image_list = new_image_list + valid_image_list2
        if len(new_list) < 4:
            for i in range(4-len(new_list)):
                new_list.append(None)
                new_image_list.append(None)
    else:
        date_string = datetime.datetime.now().strftime('%Y-%m-%d')
        valid_video_list, valid_image_list = get_user_result_video_list(uuid, date_string, 4)
        new_list = valid_video_list
        new_image_list = valid_image_list
        if len(new_list) < 4:
            date_string_yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
            valid_video_list1, valid_image_list1 = get_user_result_video_list(uuid, date_string_yesterday, 4-len(new_list))
            new_list = new_list + valid_video_list1
            new_image_list = new_image_list + valid_image_list1
        if len(new_list) < 4:
            date_string_bf_yesterday = (datetime.datetime.now() - datetime.timedelta(days=2)).strftime('%Y-%m-%d')
            valid_video_list2, valid_image_list2 = get_user_result_video_list(uuid, date_string_bf_yesterday, 4-len(new_list))
            new_list = new_list + valid_video_list2
            new_image_list = new_image_list + valid_image_list2
        if len(new_list) < 4:
            for i in range(4-len(new_list)):
                new_list.append(None)
                new_image_list.append(None)
                
    return notes, new_list[0], new_list[1], new_list[2], new_list[3]#, new_image_list[0], new_image_list[1], new_image_list[2], new_image_list[3]

with gr.Blocks(title = "Dreamoving",
               css='style.css',
               theme=gr.themes.Soft(
                        radius_size=gr.themes.sizes.radius_sm,
                        text_size=gr.themes.sizes.text_md
                    )
               ) as demo:
    with gr.Row():
        gr.HTML(f"""
                <div id=css_img_dreamoving>
                    <img id=css_img_dreamoving src='{RESOURCES.logo_img0}'>
                </div>
        """)
    
    if ENABLE_OSS_RESOURCES:
        template_videos_to_ref = []
        template_video_list = examples['template_video']
        for i in range(9):
            file_name = template_video_list[i]
            oss_path = oss_service.Prefix + "/" + oss_service.ObjectName + "/template_video/" + file_name
            print(f'template_video: {oss_path}')
            _, url = oss_service.sign(oss_path, timeout=3600*100)
            template_videos_to_ref.append(url)
    else:
        # template_videos = get_dirnames(filePath="./data/template_video", tail=".mp4")
        template_videos_to_ref = []
        template_video_list = examples['template_video']
        for i in range(9):
            # file_name = os.path.basename(template_videos[i])
            # file_path = os.path.dirname(template_videos[i])
            file_name = template_video_list[i]
            video_path = "./data/template_video/" + file_name
            template_videos_to_ref.append(video_path)                                

    # For the same style generation, after users upload a video, they can click the AI button to automatically generate a prompt.
    with gr.Accordion(label="🧭 User Guide: It is recommended to read these instructions before using!", open=False):
        gr.Markdown("""
        - ⭐️ 1. Video generation time is about 5 minutes. Due to the high number of concurrent users, the generation task may need to queue. Please click the refresh button and check the prompt message.
        - ⭐️ 2. If the input image is a cartoon picture, be sure to select "Cartoon Video Generation."
        - ⭐️ 3. The system retains up to 4 videos generated in the last two days, refreshing at midnight. Please download and save them in time.
        - ⭐️ 4. System updates generally occur between 7-8 a.m.
        """)

    input_mode = gr.Text(value="template_mode", label="input_mode", visible=False)
    with gr.Row():
        with gr.Column(scale=1):  
            with gr.Group(elem_id='show_box'):
                gr.Markdown("Enter/Select a face image")
                with gr.Column(): 
                    with gr.Group(elem_id='show_box1'):
                        with gr.Row(): 
                            ref_image = gr.Image(sources='upload', type='filepath', show_label=False, label='输入图片',elem_id='show_window_image') 
                            gr.Examples(examples['examples_images'], examples_per_page=9, inputs=[ref_image], label='')
                    
                    with gr.Row(): 
                        model_id = gr.Checkbox(label="Cartoon Video Generation", elem_id='checkbox_0', show_label=False)
                        
                    with gr.Column():
                        gr.Markdown("Select a mode: Reference-Video/Prompt")

                        with gr.Tab("Guided Style Generation") as tab0: 
                            prompt_template = gr.Textbox(placeholder="Enter prompt words to control the generation effect, such as the character, the character's clothing, the scene, etc. Supports input in Chinese/English.",label="Prompt", lines=2,interactive=True,show_label=False, text_align='left')
                            # with gr.Row():
                            #     # with gr.Group(elem_id='show_box3'):
                            #     # with gr.Group():
                            #     with gr.Column(scale=1, min_width=1):
                            #         prompt_template = gr.Textbox(placeholder="Enter prompt words to control the generation effect, such as the character, the character's clothing, the scene, etc. Supports input in Chinese/English.", label="Prompt提示词", lines=2,interactive=True,show_label=False, text_align='left')
                            #     with gr.Column(scale=1, min_width=1, elem_id='column_button'):
                            #         # prompt_caption_01 = gr.Button(value="AI Caption", elem_id='button_param1')
                            #         prompt_caption_01 = gr.Button(
                            #             value="AI",
                            #             elem_classes='btn_texture_font_file'
                            #         )                              
                            
                            with gr.Row():
                                # FIXME: the width/height setting not work here, 
                                ref_video = gr.Video(sources='upload', show_label=False, label='Input Video', autoplay=True, elem_id='show_window_video', width=224, height=360)
                                # gr.Examples(examples['template_video'], examples_per_page=9,inputs=[ref_video], label='Template Video')
                                # dataset_select = gr.Dataset(
                                #     label='Template Video',
                                #     components=[gr.Video(visible=False)],
                                #     samples=examples['template_video'],
                                #     samples_per_page=9,
                                #     type='index', # pass index or value
                                #     # min_width=400,
                                #     # elem_id='dataset',
                                #     # elem_id='template_param',
                                # )
                                gr.Examples(
                                    label='Template Video',
                                    examples=template_videos_to_ref,
                                    inputs=ref_video,
                                    outputs=[ref_video, prompt_template],
                                    fn=video_2_prompt_func,
                                    examples_per_page=9,
                                    cache_examples=True, #run_on_click=True,
                                )
                            # prompt_template = gr.Textbox(label="Prompt", lines=2,interactive=True,show_label=False, text_align='left')
                             

                        with gr.Tab("Text-to-Video") as tab1:
                            # prompt = gr.Textbox(label="Prompt", show_label=False, text_align='left')
                            example_prompts= []
                            file = open(ref_video_prompt, 'r')
                            for line in file.readlines():
                                example_prompts.append(line)
                            file.close() 
                            prompt = gr.Dropdown(label="Prompt List",choices=example_prompts,  show_label=False, allow_custom_value=True)
                                                                                
                    with gr.Row(): 
                        # Generate Button
                        run_button = gr.Button(value="Generation", elem_id='button_param') 
                        # btn = gr.Button("Result Video").style(full_width=False)
        
        with gr.Column(scale=1): 
            # gr.Markdown("Result Video",elem_id='font_style') 
            with gr.Group(elem_id='show_box2'):
                with gr.Row(elem_id='round_box'):
                    with gr.Column(scale=1, min_width=1):
                        gr.Markdown("Result Video", elem_id='font_style')
                    with gr.Column(scale=3, min_width=1):
                        user_notes = gr.Textbox(show_label=False, text_align='left', elem_id='text_style11')
                    with gr.Column(scale=1, min_width=1):
                        refresh_button = gr.Button(value="Refresh", elem_id='button_param1')
                           
                with gr.Row():
                    output_video0 = gr.Video(format="mp4", show_label=False, label="Result Video", autoplay=True, elem_id='show_window_result')
                    output_video1 = gr.Video(format="mp4", show_label=False, label="Result Video", autoplay=True,elem_id='show_window_result')
                with gr.Row():
                    output_video2 = gr.Video(format="mp4", show_label=False, label="Result Video", autoplay=True,elem_id='show_window_result')
                    output_video3 = gr.Video(format="mp4", show_label=False, label="Result Video", autoplay=True,elem_id='show_window_result')
            
    uuid = gr.Text(label="modelscope_uuid", visible=False)
    request_id = gr.Text(label="modelscope_request_id", visible=False)

    # Sample Video
    num_video = 8
    num_videos_per_row = 4
    mp4_lists = []
    if ENABLE_OSS_RESOURCES:
        mp4_url_list = get_dirnames(filePath="./data/sample_video", tail=".mp4")
        for i in range(min(num_video, len(mp4_url_list))):
            file_name = os.path.basename(mp4_url_list[i])
            oss_path = oss_service.Prefix + "/" + oss_service.ObjectName + "/template_video/" + file_name
            print(f'template_video: {oss_path}')
            _, video_url = oss_service.sign(oss_path, timeout=3600*100)
            mp4_lists.append(video_url)
    else:
        mp4_lists = get_dirnames(filePath="./data/sample_video", tail=".mp4")

    if len(mp4_lists) <= num_video:
        num_video = len(mp4_lists)
    with gr.Row():
        gr.Markdown("Sample Video",elem_id='font_style')
    with gr.Group(elem_id='show_box'):
        with gr.Column():   
            for i in range(int((num_video+num_videos_per_row-1)/num_videos_per_row)):
                with gr.Row():
                    for j in range(num_videos_per_row):
                        if i*num_videos_per_row+j < len(mp4_lists):
                            gr.Video(value=mp4_lists[i*num_videos_per_row+j],  show_label=False, interactive=False, label='result')
                        else:
                            gr.Video(interactive=False, label='result')

    refresh_button.click(
        fn=refresh_video,
        queue = False,
        inputs=[uuid, request_id],
        outputs=[user_notes, output_video0, output_video1, output_video2, output_video3]
    )
         

    # prompt_caption_01.click(
    #     fn=myHumanGen.click_button_prompt,
    #     queue = False,
    #     inputs=[uuid, request_id, input_mode, ref_image, ref_video, prompt, prompt_template, model_id],
    #     outputs=[prompt_template]
    # )
         
                            
    # dataset_select.select(fn=dataset_func, outputs=[ref_video,prompt_template])
    
    # button触发
    tab0.select(fn=tab_func_template, outputs=[prompt, input_mode]) # template mode
    tab1.select(fn=tab_func_prompt, outputs=[ref_video, input_mode]) # prompt mode
    
    def async_process(user_id, request_id, input_mode, ref_image_path, ref_video_path, input_prompt='', prompt_template='',model_id=False):
        # parm-chheck
        check_note_info = myHumanGen.valid_check(user_id, request_id, input_mode, ref_image_path, ref_video_path, input_prompt, prompt_template,model_id)
        
        if check_note_info == '':
            thread = threading.Thread(target=myHumanGen.click_button_func_async, args=(user_id, request_id, input_mode, ref_image_path, ref_video_path, input_prompt, prompt_template,model_id,))
            thread.start()
            # thread.join()
            time.sleep(5)
            
            return refresh_video(user_id, request_id)
        else:
            notes, video_0, video_1, video_2, video_3 = refresh_video(user_id, request_id)
            return check_note_info, video_0, video_1, video_2, video_3
    
    run_button.click(fn=async_process, inputs=[uuid, request_id, input_mode, ref_image, ref_video, prompt, prompt_template, model_id], outputs=[user_notes, output_video0, output_video1, output_video2, output_video3])
        
    with gr.Row():
        # DingTalk
        gr.HTML(f"""
                <div id=css_img_QRCode>
                        <img id=css_img_QRCode  src='{RESOURCES.logo_dingding}'>
                </div>
                <div id=css_img_QRCode_text>
                    DingTalk Group of Dreamoving
                </div>

        """)
        # WeChat
        gr.HTML(f"""
                <div id=css_img_QRCode>
                    <img id=css_img_QRCode src='{RESOURCES.logo_wechat}'>
                </div>
                <div id=css_img_QRCode_text>
                    WeChat Group of Dreamoving
                </div>
        """)
                
    # version
    gr.HTML(f"""
            </br>
            <div>
                <center> Version: {VERSION} </center>
            </div>
    """)

# concurrency_count, concurrency_limit, max_threads
demo.queue(api_open=False, max_size=1000).launch(
    server_name="0.0.0.0", # if os.getenv('GRADIO_LISTEN', '') != '' else "127.0.0.1",
    share=True,
    server_port=7860,
    root_path=f"/{os.getenv('GRADIO_PROXY_PATH')}" if os.getenv('GRADIO_PROXY_PATH') else ""
)


