import os
import time
import gradio as gr
import threading
from myconfigs import *
from oss_utils import ossService

from gen_client import *
myHumanGen = HumanGenService()
oss_service = ossService()

# enable oss resources, if disabled use example mp4 resources from local directory.
ENABLE_OSS_RESOURCES = True

TEST_ENABLED = os.getenv('TEST_ENABLED', 'False')

result_video_oss_url = {} # user_id, (list[signed_url), list[oss_path])]

def tab_func_template():
    prompt = ""
    return prompt, 'template_mode'
def tab_func_prompt():
    ref_video_path = None
    return ref_video_path, 'prompt_mode'
    
with open('script.txt', encoding="utf-8") as f:
    script_text_to_load_results = f.read()
    
# def dataset_func(evt: gr.SelectData):
#     ref_video_path = evt.value[0]
#     print("[dataset_func] ref_video_path: ", ref_video_path)
#     # input_prompt = 'haha'
#     if not os.path.exists(ref_video_path):
#         raise gr.Error(f"The input video {ref_video_path} is not existed!")
#     video_file_name = os.path.basename(ref_video_path)
#     __, input_prompt = myHumanGen.template_video_2_prompt(video_file_name)
#     return ref_video_path,input_prompt

def video_2_prompt_func(ref_video_path):
    print("[dataset_func] ref_video_path: %s" % ref_video_path)
    if not os.path.exists(ref_video_path):
        raise gr.Error(f"The input video {ref_video_path} is not existed!")
    video_file_name = os.path.basename(ref_video_path)
    print("[dataset_func] video_file_name: %s" % video_file_name)
    __, input_prompt = myHumanGen.template_video_2_prompt(video_file_name)
    print("[dataset_func] input_prompt: %s" % input_prompt)
    return ref_video_path,input_prompt


def get_user_result_video_list(uuid, date_string, num):
    directory='video_generation/Service/'+date_string+'/'+uuid+'/'
    for obj in oss2.ObjectIterator(oss_service.bucket, prefix=directory, delimiter='/'):
        print(f"目录存在：{directory}")
        break
    else:
        print(f"目录不存在：{directory}")
        return [],[]
    no_check_video_list = []
    no_check_timer_list = []
    for obj in oss2.ObjectIterator(oss_service.bucket, prefix=directory, delimiter = '/'):
        if obj.is_prefix():  # 判断obj为文件夹。
            file_full_path = obj.key+'result.mp4'
            exist = oss_service.bucket.object_exists(file_full_path)
            
            if not exist:
                print(f'file_full_path is not existed')
                tmp_directory=obj.key
                print(f'tmp_directory = {tmp_directory}')
                for obj_xxx in oss2.ObjectIterator(oss_service.bucket, prefix=tmp_directory, delimiter = '/'):
                    print(f'obj_xxx.key = {obj_xxx.key}')
                    if obj_xxx.is_prefix():  # 判断obj为文件夹
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

                if mb_num > 0.1: # 大于100KB
                    last_modified = object_meta.headers.get('Last-Modified')
                    # print(f"Last Modified: {last_modified}")
                    from email.utils import parsedate_to_datetime
                    # 将 HTTP-date 格式字符串转换为 datetime 对象
                    last_modified_datetime = parsedate_to_datetime(last_modified)
                    # 将 datetime 对象转换为 Unix 时间戳（整数秒）-自1970年1月1日UTC以来的秒数
                    last_modified_timestamp = int(last_modified_datetime.timestamp())
                    # print(f"Last Modified (timestamp): {last_modified_timestamp}")
                    
                    no_check_video_list.append(file_full_path)
                    no_check_timer_list.append(last_modified_timestamp)
                else:
                    print(f'文件太小: {file_full_path}')       
        else:                # 判断obj为文件。
            print(f'这不是文件夹: {obj.key}') 
            # last_modified = obj.last_modified  # 文件的最后修改时间
            # print(f"File: {obj.key}, Last Modified: {last_modified}")  
        
    valid_video_list = []
    valid_image_list = []
    if len(no_check_video_list) > 0:
        if len(no_check_video_list) > 1:
            # sort by time
            zipped_lists = zip(no_check_timer_list, no_check_video_list) # 合并为元组
            sorted_pairs = sorted(zipped_lists, key=lambda x: x[0], reverse=True) # 从大到小
            list1_sorted, list2_sorted = zip(*sorted_pairs)
            no_check_timer_list = list(list1_sorted)
            no_check_video_list = list(list2_sorted)
        
        for file_full_path in no_check_video_list:
            oss_video_path = "oss://vigen-invi/" + file_full_path
            print(f'生成的视频: {oss_video_path}')
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
        # video_oss_path = "oss://vigen-invi/video_generation/logo/runing.mp4"
        # _, video_url = oss_service.sign(video_oss_path, timeout=3600*100)
        # new_list.append(video_url)
        # img_oss_path = "oss://vigen-invi/video_generation/logo/runing.png"
        # _, img_url = oss_service.sign(img_oss_path, timeout=3600*100)
        # new_image_list.append(img_url)
        new_list.append(None)
        new_image_list.append(None)
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
                
    return notes, new_list[0], new_list[1], new_list[2], new_list[3], new_image_list[0], new_image_list[1], new_image_list[2], new_image_list[3]

with gr.Blocks(title = "追影",
               css='style.css',
               theme=gr.themes.Soft(
                        radius_size=gr.themes.sizes.radius_sm,
                        text_size=gr.themes.sizes.text_md
                    )
               ) as demo:
    with gr.Row():
        gr.HTML(f"""
            <div id='logo'>
                <div
                    style="
                        margin-left: 0px !important;
                    "
                >
                <img id='logo_img' src='{RESOURCES.logo_img0}' >
            </div>
            </br>
        """)
    
    template_videos_to_ref = examples['template_video']
    if ENABLE_OSS_RESOURCES:
        template_videos_to_ref = []
        template_video_list = examples['template_video']
        for i in range(9):
            file_name = template_video_list[i]
            oss_path = "oss://vigen-invi/video_generation/template_video1/" + file_name
            _, url = oss_service.sign(oss_path, timeout=3600*100)
            template_videos_to_ref.append(url)

    with gr.Accordion(label="🧭 使用指南：建议先阅读此说明再使用!", open=False):
        gr.Markdown("""
        - ⭐️ 1、视频生成时间在7分钟左右，由于并发人数多，生成任务可能要排队，请点击刷新按钮后查看提示信息；
        - ⭐️ 2、如果输入图像为卡通图片，一定要勾选“卡通化视频生成”。
        - ⭐️ 3、系统保留最多4个最近两天生成的视频，0点刷新，请及时下载保存。
        - ⭐️ 4、系统更新一般在早上7～8点。
        """)

    input_mode = gr.Text(value="prompt_mode", label="input_mode", visible=False)
    with gr.Row():
        with gr.Column(scale=1):  # 左侧一列
            # gr.Markdown("输入形象和动作",elem_id='font_style')
            with gr.Group(elem_id='show_box'):
                gr.Markdown("输入你的形象")
                with gr.Column(): 
                    with gr.Group(elem_id='show_box1'):
                        with gr.Row(): # 图片输入
                            #左侧图片预览
                            ref_image = gr.Image(sources='upload', type='filepath', show_label=False, label='输入图片',elem_id='show_window_image') 
                            #右侧图片列表
                            gr.Examples(examples['examples_images'], examples_per_page=9, inputs=[ref_image], label='')
                    
                    with gr.Row(): # checkbox
                        # 模型切换
                        model_id = gr.Checkbox(label="卡通视频生成", show_label=False)
                        
                    with gr.Column(): # 文字/视频输入
                        gr.Markdown("选择视频动作的参考视频或者文本描述")

                        with gr.Tab("文生视频") as tab1:
                            # prompt = gr.Textbox(label="Prompt提示词", show_label=False, text_align='left')
                            example_prompts= []
                            file = open(ref_video_prompt, 'r')
                            for line in file.readlines():
                                example_prompts.append(line)
                            file.close() 
                            prompt = gr.Dropdown(label="Prompt提示词",choices=example_prompts,  show_label=False, allow_custom_value=True)

                        with gr.Tab("同款生成") as tab0: # 视频模板
                            prompt_template = gr.Textbox(placeholder="输入提示词控制生成效果，如人物，人物的服饰、场景等，支持中/英文输入。",label="Prompt提示词", lines=2,interactive=True,show_label=False, text_align='left')
                            with gr.Row():
                                # FIXME: the width/height setting not work here, TODO: CSS 调整
                                ref_video = gr.Video(sources='upload', show_label=False, label='输入视频', autoplay=True, elem_id='show_window_video', width=224, height=360)
                                # gr.Examples(examples['template_video'], examples_per_page=9,inputs=[ref_video], label='样例视频')
                                # dataset_select = gr.Dataset(
                                #     label='样例视频',
                                #     components=[gr.Video(visible=False)],
                                #     samples=examples['template_video'],
                                #     samples_per_page=9,
                                #     type='index', # pass index or value
                                #     # min_width=400,
                                #     # elem_id='dataset',
                                #     # elem_id='template_param',
                                # )
                                gr.Examples(
                                    label='样例视频',
                                    examples=template_videos_to_ref,
                                    inputs=ref_video,
                                    outputs=[ref_video, prompt_template],
                                    fn=video_2_prompt_func,
                                    examples_per_page=9,
                                    cache_examples=True, #run_on_click=True,
                                )
                            # prompt_template = gr.Textbox(label="Prompt提示词", lines=2,interactive=True,show_label=False, text_align='left')
                                                                                
                    with gr.Row(): # 生成button
                        # 生成按钮
                        run_button = gr.Button(value="生成视频", elem_id='button_param') 
                        # btn = gr.Button("生成视频").style(full_width=False)
        
        with gr.Column(scale=1):  # 右侧一列
            # gr.Markdown("生成视频",elem_id='font_style') 
            with gr.Group(elem_id='show_box2'):
                with gr.Row():
                    with gr.Group(elem_id='box_show4'):
                        with gr.Column(scale=0.33, min_width=0.33):
                            gr.Markdown("生成视频",elem_id='font_style')
                        with gr.Column(scale=0.33, min_width=0.33):
                            user_notes = gr.Textbox(show_label=False, text_align='left', elem_id='text_style11')
                        with gr.Column(scale=0.33, min_width=0.33):
                            refresh_button = gr.Button(value="刷新", elem_id='button_param1')
                           
                with gr.Row():
                    output_video0 = gr.Video(format="mp4", show_label=False, label="Result Video", autoplay=True, elem_id='show_window_result1', elem_classes="show_window_result")
                    output_snapshot_image0 = gr.Image(sources='upload', type='filepath', show_label=False, interactive=False, elem_id='output_snapshot_image1', width=200,height=1, visible=False) 
                    output_video1 = gr.Video(format="mp4", show_label=False, label="Result Video", autoplay=True,elem_id='show_window_result2', elem_classes="show_window_result")
                    output_snapshot_image1 = gr.Image(sources='upload', type='filepath', show_label=False, interactive=False, elem_id='output_snapshot_image2', width=200,height=1, visible=False) 
                with gr.Row():
                    output_video2 = gr.Video(format="mp4", show_label=False, label="Result Video", autoplay=True,elem_id='show_window_result3', elem_classes="show_window_result")
                    output_snapshot_image2 = gr.Image(sources='upload', type='filepath', show_label=False, interactive=False, elem_id='output_snapshot_image3', width=200,height=1, visible=False) 
                    output_video3 = gr.Video(format="mp4", show_label=False, label="Result Video", autoplay=True,elem_id='show_window_result4', elem_classes="show_window_result")
                    output_snapshot_image3 = gr.Image(sources='upload', type='filepath', show_label=False, interactive=False, elem_id='output_snapshot_image4', width=200,height=1, visible=False) 
            
    uuid = gr.Text(label="modelscope_uuid", visible=False)
    request_id = gr.Text(label="modelscope_request_id", visible=False)

    # 展示生成的视频
    img_lists = []
    mp4_lists = get_dirnames(filePath="./data/sample_video", tail=".mp4")
    # mp4_listss = [[i] for i in mp4_lists]
    # gr.Markdown("样例视频",elem_id='font_style')
    # ref_video1 = gr.Video(sources='upload', height=400, show_label=False, visible=False, label='输入视频',elem_id='show_window_video')
    # with gr.Group():
    #     gr.Examples(mp4_listss, examples_per_page=12, inputs=[ref_video1], label='')

    if ENABLE_OSS_RESOURCES:
        mp4_url_list = []
        for i in range(min(12, len(mp4_lists))):
            file_name = os.path.basename(mp4_lists[i])
            # file_name = str(i) + ".mp4"
            oss_path = "oss://vigen-invi/video_generation/sample_video/" + file_name
            _, video_url = oss_service.sign(oss_path, timeout=3600*100)
            mp4_url_list.append(video_url)
        mp4_lists = mp4_url_list
        
    num_videos_per_row = 4
    num_video = 8
    if len(mp4_lists) <= num_video:
        num_video = len(mp4_lists)
    with gr.Row():
        gr.Markdown("样例视频",elem_id='font_style')
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
        outputs=[user_notes, output_video0, output_video1, output_video2, output_video3, 
                 output_snapshot_image0, output_snapshot_image1, output_snapshot_image2, output_snapshot_image3 ]
    )
                            
    # dataset_select.select(fn=dataset_func, outputs=[ref_video,prompt_template])
    
    # button触发
    tab0.select(fn=tab_func_template, outputs=[prompt, input_mode]) # 视频模板模式
    tab1.select(fn=tab_func_prompt, outputs=[ref_video, input_mode]) # prompt模式
    
    def async_process(user_id, request_id, input_mode, ref_image_path, ref_video_path, input_prompt='', prompt_template='',model_id=False):
        # 入参检查
        check_note_info = myHumanGen.valid_check(user_id, request_id, input_mode, ref_image_path, ref_video_path, input_prompt, prompt_template,model_id)
        
        if check_note_info == '':
            # 创建独立线程处理
            thread = threading.Thread(target=myHumanGen.click_button_func_async, args=(user_id, request_id, input_mode, ref_image_path, ref_video_path, input_prompt, prompt_template,model_id,))
            thread.start()
            # thread.join()
            time.sleep(5)
            
            return refresh_video(user_id, request_id)
        else:
            notes, video_0, video_1, video_2, video_3, image_0, image_1, image_2, image_3 = refresh_video(user_id, request_id)
            return check_note_info, video_0, video_1, video_2, video_3, image_0, image_1, image_2, image_3
    
    if TEST_ENABLED == "True":
        run_button.click(fn=myHumanGen.click_button_mock_test, inputs=[uuid, request_id, input_mode, ref_image, ref_video, prompt, prompt_template, model_id], outputs=[])
    else:
        # run_button.click(fn=myHumanGen.click_button_func_async, inputs=[uuid, request_id, input_mode, ref_image, ref_video, prompt, prompt_template, model_id], outputs=[])
        run_button.click(fn=async_process, inputs=[uuid, request_id, input_mode, ref_image, ref_video, prompt, prompt_template, model_id], outputs=[user_notes, output_video0, output_video1, output_video2, output_video3, 
                 output_snapshot_image0, output_snapshot_image1, output_snapshot_image2, output_snapshot_image3])
        
        
    # with gr.Accordion(label="RELEASE_NOTE", elem_id="release_note"):
        # gr.HighlightedText(label="🔊 MESSAGE", value=[("状态","开发中"),("进度", "55%")], elem_classes='info')
    with gr.Row():
        # gr.Textbox(label="RELEASE_NOTE",
        #         show_label=False,
        #     value=RELEASE_NOTE,
        #     lines=3,
        #     max_lines=3,
        #     interactive=False, scale=2)
        # 钉钉群二维码信息
        gr.HTML(f"""
                <div id=css_img_QRCode>
                        <img id=css_img_QRCode  src='{RESOURCES.logo_dingding}'>
                </div>
                <div id=css_img_QRCode_text>
                    追影需求共建钉钉群
                </div>

        """)
        # 微信群二维码信息
        gr.HTML(f"""
                <div id=css_img_QRCode>
                    <img id=css_img_QRCode src='{RESOURCES.logo_wechat}'>
                </div>
                <div id=css_img_QRCode_text>
                    追影需求共建微信群
                </div>
        """)
            
                
    # 显示版本号
    gr.HTML(f"""
            </br>
            <div>
                <center> Version: {VERSION} </center>
            </div>
    """)

    # if ENABLE_OSS_RESOURCES:
    #     snapshots = ""
    #     sample_video_list = get_dirnames(filePath="./data/sample_video", tail=".mp4")
    #     for i in range(12):
    #         if i < len(sample_video_list):
    #             file_name = os.path.basename(sample_video_list[i])
    #             oss_path = "oss://vigen-invi/video_generation/sample_video/" + file_name
    #             style = "video/snapshot,t_1000,f_jpg,w_560,h_800,m_fast"
    #             params = {'x-oss-process': style}
    #             _, url = oss_service.sign(oss_path, timeout=3600*100, params=params)
    #             snapshots = snapshots + url + ";"
        
    #     referenceVideoSnapshots = ""
    #     template_video_list = examples['template_video']
    #     for i in range(9):
    #         if i < len(template_video_list):
    #             file_name = template_video_list[i]
    #             oss_path = "oss://vigen-invi/video_generation/template_video1/" + file_name
    #             style = "video/snapshot,t_1000,f_jpg,w_56,h_80,m_fast"  #112,160
    #             params = {'x-oss-process': style}
    #             _, url = oss_service.sign(oss_path, timeout=3600*100, params=params)
    #             referenceVideoSnapshots = referenceVideoSnapshots + url + ";"
    #     format_text = script_text_to_load_results.format(snapshots, referenceVideoSnapshots)
    #     demo.load(_js = format_text)

    
demo.queue(api_open=False, concurrency_limit=1000).launch(
    server_name="0.0.0.0" if os.getenv('GRADIO_LISTEN', '') != '' else "127.0.0.1",
    share=False,
    server_port=7861,
    root_path=f"/{os.getenv('GRADIO_PROXY_PATH')}" if os.getenv('GRADIO_PROXY_PATH') else ""
)

# demo.launch(
#     server_name="0.0.0.0" if os.getenv('GRADIO_LISTEN', '') != '' else "127.0.0.1",
#     share=False,
#     enable_queue=True,
#     root_path=f"/{os.getenv('GRADIO_PROXY_PATH')}" if os.getenv('GRADIO_PROXY_PATH') else ""
# )


