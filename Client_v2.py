import cv2
import pika
import base64
import threading
from ultralytics import YOLO
from ultralytics import settings

# RabbitMQ 连接函数
def connect_to_rabbitmq():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='camera_alerts')
    return channel

# 摄像头检测和发送告警图片的函数
def detect_from_camera_and_send(camera_index, model, channel):
    cap = cv2.VideoCapture(camera_index)  # 使用不同的摄像头索引
    if not cap.isOpened():
        print(f"Failed to open camera {camera_index}")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"Failed to capture frame from camera {camera_index}. Retrying...")
            cap.release()
            cap = cv2.VideoCapture(camera_index)
            cv2.waitKey(1000)  # 等待1秒后重试
            continue

        try:
            # 使用 YOLOv8 进行人类检测
            results = model(frame)

            # 如果检测到人类，处理并发送图片告警
            if any(result.boxes.cls == 0 for result in results):  # 0 是 YOLOv8 的 "person" 类别
                annotated_frame = results[0].plot()

                # 将标注后的帧编码为 Base64
                _, buffer = cv2.imencode('.png', annotated_frame)
                encoded_image = base64.b64encode(buffer).decode()

                # 发送告警图片到队列
                channel.basic_publish(exchange='',
                                      routing_key='camera_alerts',
                                      body=encoded_image)
                print(f" [x] Detected and sent alert from camera {camera_index}")

            # 显示当前帧（可选）
            cv2.imshow(f'Camera {camera_index} Feed', frame)

        except Exception as e:
            print(f"Error processing frame from camera {camera_index}: {str(e)}")

        # 按 'q' 键退出
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 关闭摄像头
    cap.release()
    cv2.destroyAllWindows()

# 创建多线程处理 4 个摄像头
def run_multiple_cameras():
    # View all settings
    print(settings)

    # Return a specific setting
    value = settings["runs_dir"]

    model = YOLO('yolov8n.pt')  # 加载 YOLOv8 模型
    channel = connect_to_rabbitmq()  # 建立 RabbitMQ 连接

    # 创建并启动每个摄像头的线程
    threads = []
    for camera_index in range(4):  # 假设摄像头索引为 0, 1, 2, 3
        thread = threading.Thread(target=detect_from_camera_and_send, args=(camera_index, model, channel))
        threads.append(thread)
        thread.start()

    # 等待所有线程完成
    for thread in threads:
        thread.join()

# 运行检测程序
run_multiple_cameras()