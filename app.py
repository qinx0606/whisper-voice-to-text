import os
from flask import Flask, render_template, request, jsonify
import whisper
import re
from io import BytesIO
import base64
import matplotlib
matplotlib.use('Agg')  # 设置为 'Agg' 后端
import matplotlib.pyplot as plt

# 初始化 Flask 应用
app = Flask(__name__)

# 文件上传目录
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 全局模型初始化（在应用启动时加载所有模型）
models = {}

# 加载 Whisper 模型（只加载一次）
def load_models():
    global models
    models = {
        "turbo": whisper.load_model("turbo"),
        "large-v2": whisper.load_model("large-v2"),
        "large-v3": whisper.load_model("large-v3"),
    }

# 调用模型加载函数
load_models()

# 语言检测
def detect_language(text):
    chinese_chars = 0
    japanese_chars = 0
    chinese_text = []
    japanese_text = []
    
    for char in text:
        if '\u4e00' <= char <= '\u9fff':  # 汉字范围
            chinese_chars += 1
            chinese_text.append(char)
        elif '\u3040' <= char <= '\u30ff' or '\u31f0' <= char <= '\u31ff':  # 日文假名范围
            japanese_chars += 1
            japanese_text.append(char)
    
    chinese_text = ''.join(chinese_text)
    japanese_text = ''.join(japanese_text)
    return chinese_chars, japanese_chars, chinese_text, japanese_text

# 格式化函数，提取时间戳并输出格式化文本
def format_segments(segments):
    formatted_segments = []
    for segment in segments:
        start_time = segment['start']
        end_time = segment['end']
        text = segment['text']
        
        start_time_str = f"{int(start_time // 60):02}:{start_time % 60:06.3f}"
        end_time_str = f"{int(end_time // 60):02}:{end_time % 60:06.3f}"
        
        formatted_segments.append(f"[{start_time_str} --> {end_time_str}] {text}")
    return "\n".join(formatted_segments)

# 计算语言比重
def calculate_language_ratios(text):
    lines = text.strip().split("\n")
    total_chinese_chars = 0
    total_japanese_chars = 0
    total_chars = 0
    
    chinese_texts = []
    japanese_texts = []

    for line in lines:
        match = re.match(r"\[.*\] (.*)", line)
        if match:
            content = match.group(1).strip()
            chinese_chars, japanese_chars, chinese_text, japanese_text = detect_language(content)
            
            total_chinese_chars += chinese_chars
            total_japanese_chars += japanese_chars
            total_chars += chinese_chars + japanese_chars
            
            if chinese_text:
                chinese_texts.append(chinese_text)
            if japanese_text:
                japanese_texts.append(japanese_text)

    chinese_ratio = (total_chinese_chars / total_chars) * 100 if total_chars > 0 else 0
    japanese_ratio = (total_japanese_chars / total_chars) * 100 if total_chars > 0 else 0

    full_chinese_text = ' '.join(chinese_texts)
    full_japanese_text = ' '.join(japanese_texts)

    return chinese_ratio, japanese_ratio, full_chinese_text, full_japanese_text

# 可视化饼图
def plot_language_ratios(chinese_ratio, japanese_ratio):
    # 创建一个画布
    plt.figure(figsize=(6, 6), dpi=100)
    plt.rc('font',family='Times New Roman',size=16)#SimHei
    # 绘制饼图
    labels = ['Chinese', 'Japanese']
    sizes = [chinese_ratio, japanese_ratio]
    colors = ['#ff9999', '#66b3ff']
    explode = (0.1, 0) # 使汉语的部分稍微突出

    plt.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%.2f%%', shadow=True, startangle=140,
            textprops={'fontweight': 'bold'})  # 设置标签字体加粗 
    plt.title("Proportion of L1 and L2 usage\n\n\n",fontweight='bold',fontsize=20)
    plt.axis('equal')

    # 保存图表为图片
    img = BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    img_base64 = base64.b64encode(img.read()).decode('utf-8')
    return img_base64

# 首页路由
@app.route('/')
def index():
    return render_template('index.html')

# 音频上传并分析
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    model_name = request.form.get('model', 'turbo')  # 获取用户选择的模型，默认是turbo
    model = models.get(model_name)  # 获取对应模型

    if not model:
        return jsonify({"error": "Invalid model selected"}), 400  # 如果模型无效，返回错误

    # 保存文件
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)

    # 使用 Whisper 进行语音转文字
    try:
        result = model.transcribe(file_path, fp16=False)
    except Exception as e:
        return jsonify({"error": f"Error during transcription: {str(e)}"}), 500

    # 格式化语音段落
    text = format_segments(result['segments'])
    
    # 计算语言比重
    chinese_ratio, japanese_ratio, full_chinese_text, full_japanese_text = calculate_language_ratios(text)
    
    # 绘制饼图
    img_base64 = plot_language_ratios(chinese_ratio, japanese_ratio)

    # 返回分析结果
    return jsonify({
        "chinese_ratio": chinese_ratio,
        "japanese_ratio": japanese_ratio,
        "pie_chart": img_base64,
        "full_speech_to_text": text,
        "speech_to_text": result['text'],
        "full_chinese_text": full_chinese_text,
        "full_japanese_text": full_japanese_text,
        "model": model_name  # 返回所选择的模型
    })

if __name__ == "__main__":
    # 使用环境变量 PORT 来指定绑定的端口
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
