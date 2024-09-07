import cv2
import pika
import base64
import threading
from datetime import datetime
from ultralytics import YOLO
from ultralytics import settings
import time

# RabbitMQ 连接函数
def connect_to_rabbitmq():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='camera_alerts')
    return channel

# 摄像头检测和发送告警图片的函数
def detect_from_camera_and_send(camera_url, model, channel):
    cap = cv2.VideoCapture(camera_url)  # 使用 RTSP URL 作为摄像头输入
    if not cap.isOpened():
        print(f"Failed to open camera with URL {camera_url}")
        return

    detection_count = 0
    last_check_time = time.time()
    frame_counter = 0
    skip_frames = 5  # 每5帧进行一次检测

    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"Failed to capture frame from camera with URL {camera_url}. Retrying...")
            cap.release()
            cap = cv2.VideoCapture(camera_url)
            cv2.waitKey(1000)  # 等待1秒后重试
            continue

        frame_counter += 1

        # 每5帧进行一次检测
        if frame_counter % skip_frames == 0:
            try:
                # 使用 YOLOv8 进行人类检测
                results = model(frame)

                # 检测到人类，增加计数
                if any((result.boxes.cls == 0).any() for result in results):  # 0 是 YOLOv8 的 "person" 类别
                    detection_count += 1

            except Exception as e:
                print(f"Error processing frame from camera with URL {camera_url}: {str(e)}")

            current_time = time.time()
            # 每1秒检查一次
            if current_time - last_check_time >= 0.5:
                if detection_count >= 3:
                    # 检测次数满足条件，发送告警
                    annotated_frame = results[0].plot() if detection_count > 0 else None
                    encoded_image = None

                    if annotated_frame is not None:
                        _, buffer = cv2.imencode('.png', annotated_frame)
                        encoded_image = base64.b64encode(buffer).decode()

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    dev_seriesid = '111'

                    message = {
                        #'camera_url': camera_url,      # 改为摄像头 URL
                        'camera_url': 1,  # 改为摄像头 URL
                        'timestamp': timestamp,        # 时间戳
                        'image': encoded_image,        # 图片数据
                        'seriesid': dev_seriesid,      # 设备ID
                        'detection_count': detection_count  # 检测到的次数
                    }

                    channel.basic_publish(exchange='',
                                          routing_key='camera_alerts',
                                          body=str(message))
                    print(f" [x] Sent alert from camera with URL {camera_url} with {detection_count} detections at {timestamp}")

                # 重置计数器和时间
                detection_count = 0
                last_check_time = current_time
                # 调整显示帧的尺寸
        small_frame = cv2.resize(frame, (320, 240))  # 将帧调整为 320x240 的尺寸
        # 显示当前帧（可选）
        cv2.imshow(f'Camera Feed', small_frame)

        # 按 'q' 键退出
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 关闭摄像头
    cap.release()
    cv2.destroyAllWindows()

# 创建多线程处理多个摄像头
def run_multiple_cameras():
    # View all settings
    print(settings)

    # Return a specific setting
    value = settings["runs_dir"]

    model = YOLO('yolov8n.pt')  # 加载 YOLOv8 模型
    channel = connect_to_rabbitmq()  # 建立 RabbitMQ 连接

    # RTSP URLs 列表
    camera_urls = [
        "rtsp://admin:Fengzeng123@192.168.137.77:554/ISAPI/Streaming/Channels/1",
        # 可以添加更多摄像头 URL
    ]

    # 创建并启动每个摄像头的线程
    threads = []
    for camera_url in camera_urls:
        thread = threading.Thread(target=detect_from_camera_and_send, args=(camera_url, model, channel))
        threads.append(thread)
        thread.start()

    # 等待所有线程完成
    for thread in threads:
        thread.join()

# 运行检测程序
run_multiple_cameras()
