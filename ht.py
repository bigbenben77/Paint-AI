import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QGridLayout, QPushButton, QLabel,
                             QMenuBar, QMenu, QAction, QStatusBar, QScrollArea,
                             QComboBox, QSpinBox, QDoubleSpinBox, QFrame, QDialog, QDialogButtonBox,
                             QGroupBox, QRadioButton, QLineEdit, QFormLayout,
                             QMessageBox, QFileDialog, QFontDialog, QColorDialog,
                             QTabWidget, QCheckBox, QSlider, QTextEdit, QProgressBar)  # 添加缺失的类
from PyQt5.QtCore import Qt, QPoint, QRect, QTimer, QSize, QThread, pyqtSignal, QMimeData
from PyQt5.QtGui import QPainter, QPen, QColor, QPixmap, QIcon, QFont, QTransform, QBrush, QImage
from PyQt5.QtGui import QClipboard, QPainterPath  # 添加剪贴板支持和绘图路径
from PyQt5.QtGui import QFontDatabase  # 添加字体数据库支持
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog  # 添加打印支持
import base64
import random
import datetime
import requests
import json
import time
import configparser
import os

# 导入多模型配置
from paint_models_config import AI_MODEL_CONFIGS, get_model_config, get_available_models

class ColorDisplayWidget(QWidget):
    """自定义颜色显示组件，实现45度角斜向叠放效果"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fg_color = QColor(0, 0, 0)  # 前景色（黑色）
        self.bg_color = QColor(255, 255, 255)  # 背景色（白色）
        self.setFixedSize(50, 50)  # 正方形显示区域
        
    def set_foreground_color(self, color):
        self.fg_color = color
        self.update()
        
    def set_background_color(self, color):
        self.bg_color = color
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 整个区域的背景
        painter.fillRect(self.rect(), QColor(192, 192, 192))
        
        # 绘制背景色方块（右下角）
        bg_rect = QRect(15, 15, 30, 30)
        painter.fillRect(bg_rect, self.bg_color)
        painter.setPen(QPen(Qt.black, 1))
        painter.drawRect(bg_rect)
        
        # 绘制前景色方块（左上角，覆盖在背景色方块上）
        fg_rect = QRect(5, 5, 30, 30)
        painter.fillRect(fg_rect, self.fg_color)
        painter.setPen(QPen(Qt.black, 1))
        painter.drawRect(fg_rect)


class ImagePropertiesDialog(QDialog):
    """图像属性对话框"""
    def __init__(self, parent=None, current_width=527, current_height=421):
        super().__init__(parent)
        self.setWindowTitle("属性")
        self.setFixedSize(300, 280)
        
        # 保存当前画布尺寸
        self.current_width = current_width
        self.current_height = current_height
        
        # 获取当前时间作为上次保存时间
        now = datetime.datetime.now()
        last_saved = now.strftime("%Y/%m/%d %H:%M")
        
        # 创建布局
        layout = QVBoxLayout(self)
        
        # 尺寸设置
        size_group = QGroupBox()
        size_layout = QFormLayout(size_group)
        
        # 使用 QDoubleSpinBox 以支持英寸和厘米的小数值
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(1, 10000)
        self.width_spin.setValue(current_width)
        self.width_spin.setDecimals(0)  # 像素模式下无小数
        self.width_spin.valueChanged.connect(self._on_spin_value_changed)
        size_layout.addRow("宽度(W)：", self.width_spin)
        
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(1, 10000)
        self.height_spin.setValue(current_height)
        self.height_spin.setDecimals(0)  # 像素模式下无小数
        self.height_spin.valueChanged.connect(self._on_spin_value_changed)
        size_layout.addRow("高度(H)：", self.height_spin)
        
        layout.addWidget(size_group)
        
        # 单位选择
        unit_group = QGroupBox("单位")
        unit_layout = QVBoxLayout(unit_group)
        
        self.inch_radio = QRadioButton("英寸(I)")
        self.cm_radio = QRadioButton("厘米(M)")
        self.pixel_radio = QRadioButton("像素(P)")
        self.pixel_radio.setChecked(True)
        
        # 连接单位切换信号
        self.inch_radio.toggled.connect(self.on_unit_changed)
        self.cm_radio.toggled.connect(self.on_unit_changed)
        self.pixel_radio.toggled.connect(self.on_unit_changed)
        
        unit_layout.addWidget(self.inch_radio)
        unit_layout.addWidget(self.cm_radio)
        unit_layout.addWidget(self.pixel_radio)
        
        layout.addWidget(unit_group)
        
        # 颜色选择
        color_group = QGroupBox("颜色")
        color_layout = QVBoxLayout(color_group)
        
        self.black_white_radio = QRadioButton("黑白(B)")
        self.color_radio = QRadioButton("彩色(L)")
        self.color_radio.setChecked(True)
        
        color_layout.addWidget(self.black_white_radio)
        color_layout.addWidget(self.color_radio)
        
        layout.addWidget(color_group)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok |
                                      QDialogButtonBox.Cancel |
                                      QDialogButtonBox.RestoreDefaults)
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self.reset_defaults)
        button_box.button(QDialogButtonBox.RestoreDefaults).setText("默认值(D)")
        
        layout.addWidget(button_box)
        
        # 存储像素值（用于单位转换）
        self._stored_pixel_width = current_width
        self._stored_pixel_height = current_height
        
        # 保存固定默认尺寸，供"默认值"按钮使用（固定为720x520像素）
        self._original_pixel_width = 720  # 固定默认宽度
        self._original_pixel_height = 520  # 固定默认高度
        
        # DPI设置（用于英寸和厘米转换）
        self.dpi = 96  # 标准屏幕DPI
    
    def on_unit_changed(self):
        """单位切换时转换数值"""
        # 暂时断开 valueChanged 信号，避免在设置值时触发 _on_spin_value_changed
        try:
            self.width_spin.valueChanged.disconnect(self._on_spin_value_changed)
            self.height_spin.valueChanged.disconnect(self._on_spin_value_changed)
        except:
            pass  # 如果信号未连接，忽略错误
        
        if self.pixel_radio.isChecked():
            # 切换到像素
            self.width_spin.setRange(1, 10000)
            self.height_spin.setRange(1, 10000)
            self.width_spin.setValue(self._stored_pixel_width)
            self.height_spin.setValue(self._stored_pixel_height)
            self.width_spin.setSuffix("")
            self.height_spin.setSuffix("")
            self.width_spin.setDecimals(0)
            self.height_spin.setDecimals(0)
            
        elif self.inch_radio.isChecked():
            # 切换到英寸 (限制最大100英寸，相当于9600像素@96DPI)
            self.width_spin.setRange(0.1, 100.0)
            self.height_spin.setRange(0.1, 100.0)
            width_inch = self._stored_pixel_width / self.dpi
            height_inch = self._stored_pixel_height / self.dpi
            self.width_spin.setValue(round(width_inch, 2))
            self.height_spin.setValue(round(height_inch, 2))
            self.width_spin.setSuffix(" in")
            self.height_spin.setSuffix(" in")
            self.width_spin.setDecimals(2)
            self.height_spin.setDecimals(2)
            
        elif self.cm_radio.isChecked():
            # 切换到厘米 (限制最大250厘米，相当于约9449像素@96DPI)
            self.width_spin.setRange(0.1, 250.0)
            self.height_spin.setRange(0.1, 250.0)
            width_cm = (self._stored_pixel_width / self.dpi) * 2.54
            height_cm = (self._stored_pixel_height / self.dpi) * 2.54
            self.width_spin.setValue(round(width_cm, 2))
            self.height_spin.setValue(round(height_cm, 2))
            self.width_spin.setSuffix(" cm")
            self.height_spin.setSuffix(" cm")
            self.width_spin.setDecimals(2)
            self.height_spin.setDecimals(2)
        
        # 重新连接 valueChanged 信号
        self.width_spin.valueChanged.connect(self._on_spin_value_changed)
        self.height_spin.valueChanged.connect(self._on_spin_value_changed)
    
    def _on_spin_value_changed(self):
        """监听 width_spin 和 height_spin 的变化，将显示的值反向转换回像素值"""
        if self.pixel_radio.isChecked():
            # 像素模式下，QDoubleSpinBox的值已经是整数（因为decimals=0）
            self._stored_pixel_width = int(self.width_spin.value())
            self._stored_pixel_height = int(self.height_spin.value())
        elif self.inch_radio.isChecked():
            self._stored_pixel_width = int(self.width_spin.value() * self.dpi)
            self._stored_pixel_height = int(self.height_spin.value() * self.dpi)
        elif self.cm_radio.isChecked():
            self._stored_pixel_width = int((self.width_spin.value() / 2.54) * self.dpi)
            self._stored_pixel_height = int((self.height_spin.value() / 2.54) * self.dpi)
    
    def on_accept(self):
        """确定时检查性能限制"""
        # 确保像素值已更新（调用 _on_spin_value_changed 来更新 _stored_pixel_width/height）
        self._on_spin_value_changed()
        
        # 性能限制检查
        max_pixels = 10000 * 10000  # 1亿像素
        total_pixels = self._stored_pixel_width * self._stored_pixel_height
        
        if total_pixels > max_pixels:
            QMessageBox.warning(
                self,
                "尺寸过大",
                f"图像尺寸过大，可能导致性能问题！\n\n"
                f"当前尺寸: {self._stored_pixel_width} x {self._stored_pixel_height} ({total_pixels:,} 像素)\n"
                f"建议最大: 10000 x 10000 ({max_pixels:,} 像素)\n\n"
                f"请减小尺寸后重试。"
            )
            return
        
        # 警告大尺寸图像
        warning_pixels = 5000 * 5000  # 2500万像素
        if total_pixels > warning_pixels:
            reply = QMessageBox.question(
                self,
                "确认大尺寸",
                f"您选择的图像尺寸较大:\n"
                f"{self._stored_pixel_width} x {self._stored_pixel_height} ({total_pixels:,} 像素)\n\n"
                f"这可能会消耗较多内存并影响性能。\n\n"
                f"是否继续？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        self.accept()
    
    def reset_defaults(self):
        """重置为默认值"""
        self._stored_pixel_width = self._original_pixel_width
        self._stored_pixel_height = self._original_pixel_height
        self.pixel_radio.setChecked(True)
        self.color_radio.setChecked(True)
        # 调用单位切换来更新显示
        self.on_unit_changed()
    
    def get_dimensions(self):
        """获取像素尺寸"""
        return self._stored_pixel_width, self._stored_pixel_height
    
    def is_color_mode(self):
        """是否为彩色模式"""
        return self.color_radio.isChecked()


class AISetupDialog(QDialog):
    """AI设置对话框"""
    def __init__(self, parent=None, current_settings=None):
        super().__init__(parent)
        self.setWindowTitle("AI接入设置")
        self.setFixedSize(550, 500)  # 稍微增加高度以容纳更多设置
        
        # 加载当前设置
        self.settings = current_settings or {}
        
        # 创建布局
        layout = QVBoxLayout(self)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        
        # ====== 选项卡1: 基本设置 ======
        tab1 = QWidget()
        tab1_layout = QVBoxLayout(tab1)
        tab1_layout.setContentsMargins(10, 10, 10, 10)
        tab1_layout.setSpacing(10)
        
        # AI模型选择
        tab1_layout.addWidget(QLabel("AI模型选择:"))
        self.model_combo = QComboBox()
        
        # 获取可用模型列表
        available_models = get_available_models()
        self.model_combo.addItems(available_models)
        
        # 设置当前模型
        current_model = self.settings.get('model', '豆包-Seedream')
        index = self.model_combo.findText(current_model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        
        # 连接模型切换信号
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        
        tab1_layout.addWidget(self.model_combo)
        
        # 模型描述标签
        self.model_description_label = QLabel()
        self.model_description_label.setStyleSheet("color: gray; font-size: 10px; padding: 5px; background-color: #F0F0F0; border-radius: 3px;")
        self.model_description_label.setWordWrap(True)
        tab1_layout.addWidget(self.model_description_label)
        
        # 初始化模型描述
        self.update_model_description()
        
        tab1_layout.addSpacing(10)
        
        # ====== 新增: API端点设置 ======
        tab1_layout.addWidget(QLabel("API端点:"))
        self.api_base_url_edit = QLineEdit()
        self.api_base_url_edit.setText(self.settings.get('api_base_url', 'https://ark.cn-beijing.volces.com/api/v3'))
        self.api_base_url_edit.setPlaceholderText("输入API基础URL")
        tab1_layout.addWidget(self.api_base_url_edit)
        
        self.image_endpoint_edit = QLineEdit()
        self.image_endpoint_edit.setText(self.settings.get('image_endpoint', '/images/generations'))
        self.image_endpoint_edit.setPlaceholderText("输入图像生成端点路径")
        tab1_layout.addWidget(self.image_endpoint_edit)
        
        tab1_layout.addSpacing(10)
        
        # ====== 新增: 模型名称设置 ======
        tab1_layout.addWidget(QLabel("模型名称:"))
        self.model_name_edit = QLineEdit()
        self.model_name_edit.setText(self.settings.get('model_name', 'doubao-seedream-4-5-251128'))
        self.model_name_edit.setPlaceholderText("输入具体的模型名称")
        tab1_layout.addWidget(self.model_name_edit)
        
        tab1_layout.addSpacing(10)
        
        # ====== 新增: 请求超时设置 ======
        tab1_layout.addWidget(QLabel("请求超时时间 (秒):"))
        timeout_layout = QHBoxLayout()
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 300)
        self.timeout_spin.setValue(self.settings.get('timeout', 60))
        self.timeout_spin.setSuffix(" 秒")
        timeout_layout.addWidget(self.timeout_spin)
        timeout_layout.addStretch()
        tab1_layout.addLayout(timeout_layout)
        
        tab1_layout.addSpacing(10)
        
        # 自动保存
        self.auto_save_check = QCheckBox("自动将生成结果应用到画布")
        self.auto_save_check.setChecked(self.settings.get('auto_apply', True))
        tab1_layout.addWidget(self.auto_save_check)
        
        tab1_layout.addStretch()
        tab_widget.addTab(tab1, "基本设置")
        
        # ====== 选项卡2: API密钥和图像参数 ======
        tab2 = QWidget()
        tab2_layout = QVBoxLayout(tab2)
        tab2_layout.setContentsMargins(10, 10, 10, 10)
        tab2_layout.setSpacing(10)
        
        # API密钥
        tab2_layout.addWidget(QLabel("API密钥:"))
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setText(self.settings.get('api_key', 'user-modified-api-key-12345'))
        self.api_key_edit.setPlaceholderText("请输入您的API密钥")
        tab2_layout.addWidget(self.api_key_edit)
        
        tab2_layout.addSpacing(10)
        
        # ====== 新增: 图像尺寸设置 ======
        tab2_layout.addWidget(QLabel("图像尺寸 (宽x高):"))
        size_layout = QHBoxLayout()
        self.size_combo = QComboBox()
        self.size_combo.addItems([
            "2048x1800 (默认)",
            "1024x1024",
            "512x512",
            "720x520 (画布大小)",
            "自定义..."
        ])
        current_size = self.settings.get('size', '2048x1800 (默认)')
        index = self.size_combo.findText(current_size)
        if index >= 0:
            self.size_combo.setCurrentIndex(index)
        self.size_combo.currentTextChanged.connect(self.on_size_changed)
        
        # 自定义尺寸输入框
        self.custom_size_edit = QLineEdit()
        self.custom_size_edit.setPlaceholderText("格式: 宽x高 (如: 1024x768)")
        self.custom_size_edit.setVisible(False)
        self.custom_size_edit.setText(self.settings.get('custom_size', ''))
        
        size_layout.addWidget(self.size_combo)
        size_layout.addWidget(self.custom_size_edit)
        size_layout.addStretch()
        tab2_layout.addLayout(size_layout)
        
        tab2_layout.addSpacing(10)
        
        # ====== 新增: 图像数量设置 ======
        tab2_layout.addWidget(QLabel("一次生成的图像数量:"))
        n_layout = QHBoxLayout()
        self.n_spin = QSpinBox()
        self.n_spin.setRange(1, 10)
        self.n_spin.setValue(self.settings.get('n', 1))
        n_layout.addWidget(self.n_spin)
        n_layout.addStretch()
        tab2_layout.addLayout(n_layout)
        
        tab2_layout.addSpacing(10)
        
        # ====== 新增: 图像质量选择 ======
        tab2_layout.addWidget(QLabel("图像质量:"))
        quality_layout = QHBoxLayout()
        self.quality_standard_radio = QRadioButton("标准 (standard)")
        self.quality_hd_radio = QRadioButton("高清 (hd)")
        self.quality_standard_radio.setChecked(self.settings.get('quality', 'standard') == 'standard')
        self.quality_hd_radio.setChecked(self.settings.get('quality', 'standard') == 'hd')
        
        quality_layout.addWidget(self.quality_standard_radio)
        quality_layout.addWidget(self.quality_hd_radio)
        quality_layout.addStretch()
        tab2_layout.addLayout(quality_layout)
        
        tab2_layout.addSpacing(10)
        
        # ====== 新增: 图像风格选择 ======
        tab2_layout.addWidget(QLabel("图像风格:"))
        style_layout = QHBoxLayout()
        self.style_vivid_radio = QRadioButton("生动 (vivid)")
        self.style_natural_radio = QRadioButton("自然 (natural)")
        self.style_vivid_radio.setChecked(self.settings.get('style', 'vivid') == 'vivid')
        self.style_natural_radio.setChecked(self.settings.get('style', 'vivid') == 'natural')
        
        style_layout.addWidget(self.style_vivid_radio)
        style_layout.addWidget(self.style_natural_radio)
        style_layout.addStretch()
        tab2_layout.addLayout(style_layout)
        
        tab2_layout.addSpacing(10)
        
        # 显示/隐藏密钥
        self.show_key_check = QCheckBox("显示API密钥")
        self.show_key_check.toggled.connect(self.toggle_key_visibility)
        tab2_layout.addWidget(self.show_key_check)
        
        tab2_layout.addStretch()
        
        # 帮助文本 - 更新为豆包API相关
        help_text = QLabel(
            "豆包AI设置提示:\n"
            "• API密钥: 从豆包开发者平台获取\n"
            "• 图像尺寸: 要求至少3686400像素 (2048x1800)\n"
            "• 模型: doubao-seedream-4-5-251128\n"
            "• 默认端点是: https://ark.cn-beijing.volces.com/api/v3"
        )
        help_text.setStyleSheet("color: gray; font-size: 9px; padding: 5px; background-color: #F0F0F0; border-radius: 3px;")
        help_text.setWordWrap(True)
        tab2_layout.addWidget(help_text)
        
        tab_widget.addTab(tab2, "API和图像参数")
        
        # ====== 选项卡3: 高级设置 ======
        tab3 = QWidget()
        tab3_layout = QVBoxLayout(tab3)
        tab3_layout.setContentsMargins(10, 10, 10, 10)
        tab3_layout.setSpacing(10)
        
        # 生成质量
        tab3_layout.addWidget(QLabel("生成质量 (高级控制):"))
        quality_slider_layout = QHBoxLayout()
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(1, 10)
        self.quality_slider.setValue(self.settings.get('quality_level', 7))
        self.quality_label = QLabel(str(self.quality_slider.value()))
        self.quality_slider.valueChanged.connect(
            lambda v: self.quality_label.setText(str(v))
        )
        quality_slider_layout.addWidget(self.quality_slider)
        quality_slider_layout.addWidget(self.quality_label)
        tab3_layout.addLayout(quality_slider_layout)
        
        tab3_layout.addSpacing(10)
        
        # 创意度 (温度)
        tab3_layout.addWidget(QLabel("创意度 (温度):"))
        temp_layout = QHBoxLayout()
        self.temp_slider = QSlider(Qt.Horizontal)
        self.temp_slider.setRange(0, 100)
        self.temp_slider.setValue(self.settings.get('temperature', 70))
        self.temp_label = QLabel(f"{self.temp_slider.value()}%")
        self.temp_slider.valueChanged.connect(
            lambda v: self.temp_label.setText(f"{v}%")
        )
        temp_layout.addWidget(self.temp_slider)
        temp_layout.addWidget(self.temp_label)
        tab3_layout.addLayout(temp_layout)
        
        tab3_layout.addSpacing(15)
        
        # ====== 新增: 重置默认值按钮 ======
        reset_button = QPushButton("重置为默认值")
        reset_button.clicked.connect(self.reset_to_defaults)
        reset_button.setStyleSheet("""
            QPushButton {
                background-color: #E8E5D8;
                border: 1px solid #808080;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #D4D0C8;
            }
        """)
        tab3_layout.addWidget(reset_button)
        
        tab3_layout.addStretch()
        tab_widget.addTab(tab3, "高级设置")
        
        layout.addWidget(tab_widget)
        
        # 按钮盒
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def on_model_changed(self, model_name):
        """模型切换时更新配置"""
        # 获取新模型的默认配置
        new_config = get_model_config(model_name)
        
        # 更新界面显示
        self.update_model_description()
        
        # 更新API配置
        self.api_base_url_edit.setText(new_config.get('api_base_url', ''))
        self.image_endpoint_edit.setText(new_config.get('image_endpoint', ''))
        self.model_name_edit.setText(new_config.get('model_name', ''))
        self.api_key_edit.setText(new_config.get('api_key', ''))
        self.timeout_spin.setValue(new_config.get('timeout', 60))
        
        # 更新图像参数
        image_size = new_config.get('image_size', '1024x1024')
        index = self.size_combo.findText(image_size)
        if index >= 0:
            self.size_combo.setCurrentIndex(index)
        else:
            self.size_combo.setCurrentText("自定义...")
            self.custom_size_edit.setText(image_size)
        
        self.n_spin.setValue(new_config.get('n', 1))
        
        # 更新质量和风格
        quality = new_config.get('quality', 'standard')
        if quality == 'hd':
            self.quality_hd_radio.setChecked(True)
        else:
            self.quality_standard_radio.setChecked(True)
        
        style = new_config.get('style', 'vivid')
        if style == 'natural':
            self.style_natural_radio.setChecked(True)
        else:
            self.style_vivid_radio.setChecked(True)
        
        # 更新高级设置
        self.quality_slider.setValue(new_config.get('quality_level', 7))
        self.temp_slider.setValue(new_config.get('temperature', 70))
    
    def update_model_description(self):
        """更新模型描述"""
        current_model = self.model_combo.currentText()
        if current_model in AI_MODEL_CONFIGS:
            description = AI_MODEL_CONFIGS[current_model].get('description', '')
            self.model_description_label.setText(f"模型描述: {description}")
        else:
            self.model_description_label.setText("模型描述: 暂无描述")
    
    def on_size_changed(self, text):
        """图像尺寸选择改变时显示/隐藏自定义输入框"""
        if text == "自定义...":
            self.custom_size_edit.setVisible(True)
            self.size_combo.hide()
        else:
            self.custom_size_edit.setVisible(False)
            self.size_combo.show()
    
    def toggle_key_visibility(self, show):
        """切换API密钥可见性"""
        if show:
            self.api_key_edit.setEchoMode(QLineEdit.Normal)
        else:
            self.api_key_edit.setEchoMode(QLineEdit.Password)
    
    def reset_to_defaults(self):
        """重置为默认值"""
        # 获取当前模型的默认配置
        current_model = self.model_combo.currentText()
        default_config = get_model_config(current_model)
        
        # 基本设置
        self.api_base_url_edit.setText(default_config.get('api_base_url', ''))
        self.image_endpoint_edit.setText(default_config.get('image_endpoint', ''))
        self.model_name_edit.setText(default_config.get('model_name', ''))
        self.api_key_edit.setText(default_config.get('api_key', ''))
        self.timeout_spin.setValue(default_config.get('timeout', 60))
        
        # API和图像参数
        image_size = default_config.get('image_size', '1024x1024')
        self.size_combo.setCurrentText(image_size)
        self.custom_size_edit.setText("")
        self.custom_size_edit.setVisible(False)
        self.size_combo.show()
        self.n_spin.setValue(default_config.get('n', 1))
        
        # 设置质量和风格
        quality = default_config.get('quality', 'standard')
        if quality == 'hd':
            self.quality_hd_radio.setChecked(True)
        else:
            self.quality_standard_radio.setChecked(True)
        
        style = default_config.get('style', 'vivid')
        if style == 'natural':
            self.style_natural_radio.setChecked(True)
        else:
            self.style_vivid_radio.setChecked(True)
        
        # 高级设置
        self.quality_slider.setValue(default_config.get('quality_level', 7))
        self.temp_slider.setValue(default_config.get('temperature', 70))
        
        # 更新模型描述
        self.update_model_description()
        
        QMessageBox.information(self, "重置成功", f"已重置为 {current_model} 的默认配置值！")
    
    def get_settings(self):
        """获取所有设置"""
        # 处理图像尺寸
        size_text = self.size_combo.currentText()
        if size_text == "自定义..." and self.custom_size_edit.text():
            image_size = self.custom_size_edit.text()
        elif "(默认)" in size_text:
            image_size = "2048x1800"
        else:
            # 提取数字部分
            import re
            match = re.search(r'(\d+)x(\d+)', size_text)
            if match:
                image_size = f"{match.group(1)}x{match.group(2)}"
            else:
                image_size = "2048x1800"
        
        # 处理图像质量
        if self.quality_standard_radio.isChecked():
            quality = "standard"
        else:
            quality = "hd"
        
        # 处理图像风格
        if self.style_vivid_radio.isChecked():
            style = "vivid"
        else:
            style = "natural"
        
        # 获取当前模型
        current_model = self.model_combo.currentText()
        
        # 获取模型的基础配置
        base_config = get_model_config(current_model)
        
        return {
            # 基础API配置
            'api_base_url': self.api_base_url_edit.text(),
            'image_endpoint': self.image_endpoint_edit.text(),
            'model_name': self.model_name_edit.text(),
            'api_key': self.api_key_edit.text(),
            'timeout': self.timeout_spin.value(),
            'image_size': image_size,
            'n': self.n_spin.value(),
            'quality': quality,
            'style': style,
            
            # 模型信息和描述
            'model': current_model,
            'description': base_config.get('description', ''),
            'max_tokens': base_config.get('max_tokens', 2048),
            
            # 全局设置
            'auto_apply': self.auto_save_check.isChecked(),
            'quality_level': self.quality_slider.value(),
            'temperature': self.temp_slider.value(),
            'custom_size': self.custom_size_edit.text()
        }


class AboutDonationDialog(QDialog):
    """关于画图AI - 捐赠对话框"""
    WECHAT_QR_BASE64 = """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bef9V65cydPCrm1BEOzYscNF6t33GEWRr3o6a7xSTw+bHIjooosu+t73vleOinL6BvQcC7bWXnHFFWma1ut1t10p9ZWvfOUHP/hBhxxrrU899dRqtcpz+l2VhQ0DiDgwMHDZZZe5w7LLChHf9773nXnmmeWPJEkyNjb29re/fXYJNVOzevXqb37zmwBQrVbZ5MsdRtlrjIjc8x144IE//elPy35evhsXXHDBt771LSdk3MixsTF2IMx6mXOl1D/+4z++/OUvZ9vcZFFdREySJAiCf/mXf3n66ad5oytGevjhh1911VXlkDTPQH7ta1/7/e9/P+39tNaGYbh9+3a2oEx7Ldbaf/u3f8vz3LlWePuPfvSj888/35XV5r5HSnnWWWeVfei8nUtylx2BWZbV6/V3vOMd3KO7cw0NDb3yla/84Q9/WF4RGACyLDvrrLO4AHc5fn3KKadceeWV5YYBQJqmXAe4Y03k97///e9///unvl7PZHilnh4esOR5vmXLlt/+9rflJ8EVq+MMiKmPwz/ZY489ltM0yk/C0NAQ2zzYJsVYa++++27W3MlcZezxkFKuXLnSmXB5Oz9UL3rRi8ovATz19NRTT3HC5LwPq5VSxxxzDOsaD+jYNdEx6cfP8NKlSwcHBzsqrxLRtm3bbr/99rI9kbV1CkdgL2RZdthhhx199NFTF8t3iZqPPPLI/fff77YHQZCm6bJly4488sjy2JCv9L777nvooYemndNzaX69/GAAIIqi1atXY7ucodt+9913c2fDvyJ2jgPA+vXryx8fGBhIkqTD78y9RavVuueee6CUrskziscee+zxxx8Pu+YBZFl288031+v18rtIpVI56aST1qxZwy5yt91au379ev6lYamI65vf/OZpr9czGT5OPT38MLAil+U1iiKXOtijgrhhVLkGsTFmcHCQM83K8sE+M87KneyALGFa64npJ86lV1YELm3KaXWzXi5rCrgZzsjMnUSH84xf2FmXy/fTWQh4MTC3HUvW47l0LUKIWq3mEtC77sNNCoKgnK7CV8TpMENDQ+WejyNj3Kpe2sZ5ify608v958wRPmP5XnH73ZIIQRCwlJd/P9RenasjIZMvZGBgAHZdNp6PP9HCyP85sVJuq9VyPXHH75mvkcc3016jpxf8mHp6+NfPOlI2rvJLJVt3yzWdpzgOB+/40XIP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"""
    ALIPAY_QR_BASE64 = """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tm0jQh2apWLYGlFJtTMswggQb/C6UBD1WeLrHZ0m33Vdx3HqDCQhlLxStyXxTzTKGKoC63EhJev6Phj84k/9J9BFBLV34YeONqhMT1XbiQup4JpE6H99YB9AXAluR92UXnwycS0AO/LocqOJZ4WfcrQrNC6d6IMbF9P6GULwhBMvXmsXMtTHeIwYDAbDpMFItsFgMEwajGQbDAbDpMHYsncMlmUdcMABp59+emK57LbbbnvggQewhlnH/Ldw4cLzzz+fVZI1g9dff/2ss86qv/zVCGpZ9bnnntO327ady+W+8Y1vTJ8+XV9iGh4ehgvd4OBgNpvFwum8efN+9rOfqX3g5f3b3/72pptu0u83m81edtllnuchvYnruoODg1u2bDn99NPHbGd/fz+qUMpK0QAiOuyww/7mb/5G7YMkIatXrz7jjDP063Z2di5fvnyXXXZpIfF3Lpe76KKLpk2blnj+Ong+e+65J9y3mzo/CvS88MILV199dSLX9qmnnnrQQQdRpdyBEGLDhg033HDDiy++2NPT06AfPRZdiKijo+OLX/zi4sWLlUdjI81Ty4lnnXXW4YcfrlLCFovFMAyvuuoq3QNKCHHggQeeddZZcGFq6jkYqmIke4exaNGiU089VeXLB88+++zvf/97hIfUcoNNpVKzZ8/+9Kc/3dnZqcv697//fQhinXRUjVArBaht2319fSeccMKCBQv07Y899tjy5ctTqVSxWGSMpdNp3/evu+66L37xi/o5N23adM011/z5z3/Wj91///0vu+wyHIW4Fdd1V6xYcfPNN4/ZTrWui7gk+JPst99++nWx/Pv1r3/95ptv1uVv9uzZp5122owZM+qEvdTC87yjjz76Ax/4QJ19qi6iNgg08eWXX7711lv1d8BxnA9+8IMHHnggbbua91//9V9PP/20KovRyPnxhuRyuWXLlqlilc2286CDDlqyZIkqvuN53ksvvXT99de/8sorap84jkul0pe//GXElzV7CcNojGTvGKIoGhwchNPbaE+G+sPkUqmk4vT0z8B13c7OTuRy257qBMplLaFl5XJZ1dXVuxl4vKlCBPB7g1Ozfs44jru6uuSo8oyDg4N9fX3w00CI4/Tp0xuRHqQ5xNngNieEQACe2iefz8M/PfFIlSdiC32bqvhTx4cSDcMVm5UqvdBEItmseqp6ZwClHh35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fn8NjTGCpuzG4ft+b2/vhg0boHCquA88j+vXrw8t6UQikaampr322otrGgC5XO75558HkYW0fdtFU1PTlClT4IjkSoA9PT2qe9G27fXr13d3dyNtbMXzYHEsEokkEomRXDebzT777LPQCI/Ew97Z2QlNAicL5YQbrCauaHFLkoaQgoSUgZSOsTX7UmBHpCUqKFWYssv/IsknEmRIIX0ppaBACMMPXGkYSI4Kf7FaTWKb40s57XAL69ev/8lPfmLbdlNTE5VSHgZBkMvlDj744GpptqiUYHrGjBns0a6hGBkJsDg8PDy8ePFiVTGCdK9z5sxh7zkWSAuFArKgIAdsxXMWi8V169ZxGlXePm3atJaWFiT/Qx3LpqamN954Qw0jcBxnzZo1CE3QE5FRgabsHcJvf/vbG264gUpBIuVIJBLZbBZ5UNXtvu/PmzfvxhtvjEaj6qdy4403vv/970eCtxoJLSvi0ksvvfjiiyORSKFQQN61IAguvPDC559/nvfxPG+//fa78847Ozs7q31CqKvi+/748eNHct0lS5accsopEBuMpOTghRde+IlPfALrXfF4fNq0aRyjAcJav359f39/pUOlNJxSmmoRj8amTdszkNIyTaIKVrmkysHkgqSQ/lZKF0RCSNMiw8jls2++udbzfDAa1lQnTZo0bty42nc0c+bMM8444zOf+czGjRuxqBiPx6WUp5xyyh//+McaOc058gU5HUeYxq8GPM9LJBLLly8/6aST1KFCCLFgwYJHHnmEfThBEDiOc/bZZz/77LPYWCPXeaFQwDNSLY8rrrjiP//zP6HsxCi1fv36888/X61xiiE8k8k0IEjVqAhN2Y0DK+8bN26soUdG0ASVmWn4SDo7O2nbBfpCoZDP55Hnut6s8IODg2qVL9Q9SafTatJXTOoRI1PNiIb+ocZNheA4Tm9vr23bg4ODI7GkfvzjH997772RSCSXyx1wwAG33XbbhAkTuEaP53n333//rbfeWn6gJPIMPr/cd+bMH3z/e1O7p3iBZxlGRYu6IkkIgvdkqwQkXyjEYsl8ofDsC4svuehiZBOlUl997nOfO/fcc6vNHmDVmqaZSCQKhcKWLVsQZJjP54MgyGazbW1tNfKPw1qH2g/Za3fExMY5s9msZVmhMQ/5uFtaWrgODhGl02nP8wYGBhC1WO1xY8IBIyB07+PHj0cKdTy4bDa7ceNG9X3DO6yTZY8iNGU3Dp47w6FZcR8Iq6nMOYvZN2u2eDtCjcGY9U4kOSgRGi/wdah0pBACYeUsNStH7aCYcuBeaov8VAwODm7ZsgUtbG1t5SJYcBDbtt3X17dq1apKhwrftIkESSIK4pGklJYfEJEdVPGAVKNsg3xJovTPCsjwpBjK5VevWZ3L5tgZ4rru4OBgDfE72sx5zzEKIusAnmyNfgaRQYuNKogcUF6z/2oB14W7JvQsIpEIXCIwivGSoCw6Dqn2DnPlxlBi2EKhgE8At5DL5VpaWkK5GZipNWWPFjRl7xDwxYbKayHiABYTV6gJGRqIUoOBpr7iqHSDMh+szsY3Fjp/+UwT1jGSPICUEUGuTpAR8oA67rWpodyuRHu4TBpvx2eMOwVZlO/DgR7q5BrfPIuaZansLILx+FhEf8CtLJ0ClcxjQ/oWBYaURIEIqgwVUhqGEQQoZfuv+/U9H5GlpmVFLVu6bhxDh+vxpfFcWARdEVyHKJFI5PP5YrHIqnYiApWrjhG4j8Dj6GHVLYYnwi5j3geAGV67wgtnICnXZeO5YOrAybVR0YIdIxg7Qzm18SvXV6KSKz8Wi+GhwIRvampauXJlS0tLX19fte5ioFd1hfUGoCl79MGUCp9mEATw24b2yefzKDKtvrXI7IHoNS6HCoc474NaXKDm0FCRy+WQ4icajWYymWw2y2Y+wN5STisxcvDYg6urf2KhG8gCN6tel1kAH796INt9MO3Lw0A8z+OQPLXJrlMsFgrO1mjDyk6kIAgM2/Y9PxKJiG22S4QRst8/Eok4xarrhPWCeyMUo8+BkTXWacGMPIDxdozH1JDFipaERnqMsnhebETjxQvlltkuvXIoEOZJI2kSBgmtZ68XmrJHH+z4M00TjtFyi1hutf6CUAX0eDw+MDBApdkodgut6fFKUaFQUOmgUCi0tbXh00L2pdbW1lDQWlAqStlA8GQ0GsVNhVb/YVSyuALnD2Www8hUrl/GMh0MT9j+UkroLhige7CVengkEkmlUrhWNRbDAID/VXaAUY/Ox7RGSlmvRKcGODMfcgPwdlGqoV7bEYF3JrQdZ+M5TV3tQbAPrshFkzEbA5XzmWFehGZR/GSrBUByCH4o+2M14EEjv1VjcbxvW2jKHn3Mnz//sMMOQ1wcDN6+vr777rtPXRGybfvFF1+8+eabSYnWIyLTNK+++mpmmVgshmPVlFKWZU2bNu1973vf+PHjVaVKNBpduHAhe1FxhuOOO+7YY49Vm9fd3c3LfXXdV7FYHDdu3Kc+9amBgQGVOleuXPmnP/2pWCzyjUSj0aOPPvqII45Q27x+/fpHHnmkt7dX/aTXrVt36623Iqwfhn8QBH/5y1/U64LK582bd8ABB6hWp+u6t99+O6zCaku1MOE/+MEPzpkzR93e399/77339vX1qVXhVanDDgIjwXPPPfftb39bdTJEo9ETTjhh//33r5GPt1gsJpPJV1999fe//716X7ZtP/vssxh76i0g5/v+I488ksvlisUiWwnpdPr111/npKywssePH//JT35SHb0sy3rqqaf+8pe/1FArwlofP378BRdcsGnTpu2259BDDw1GVjJNIwRN2aMDTC3h1zvllFM++clP8tQ4CII1a9Y8/PDDKmW7rrt06dKrr746dJ6bbrppwYIFPP91HCebzT7++OMqZXue193dfe211zY1NamW40033XTFFVdwS2D4PP7443Pnzh2Ve0QRy8suuyy0/dFHH73//vuxcArHtBDi5JNPPvfcc3mfYrG4adOmV199dc2aNeqH2tPTc91119W+LizWM88888Mf/rB67NKlS+fPn1+ueVcB90JbW9uBBx6oWrvFYvF73/veihUrOCiGMSo8gk544YUXXnjhBXW7ZVn777//vvvuW8OihzNt+fLlX/va18ot1tq5PqpBSrlo0aJFixbV2AcLJ52dnVdccYVa+9HzvFtvvfWpp56qIWFC1H40Gr3kkkvqatiOrLW+PaEr12loaGjsNtCUraGhobHbQFO2hoaGxm4D7ctuHPCTklIU0ShlqIBIC+JTYOR5hHEsXNK8uK86WJPJJJ9cdS8KIaABYFUWhBAjjKJElA3kdJxQYiSuRviaubIJJMChAGiWiMVisRqrWHy2et210Wi0WCyqFbYAKEMaU5JBRwHhmnovEGhC0czCx2KxiK5j6XTFc3LQabl4hsErgbTtc2fVNmcIQUdBSY3W4vbLte0jBI4KLedCAQUFegPn1BhdaMreISBaN7TRNM1cLsffjGmaw8PDI2SNIAggAuGPNpPJJBIJNe1UoVDAxxnKQ4KfORYRP2Sz2Wr5T0KAkIATUNi2nc/nRxIDmclkQCKqcC2fz6vXRWIgKhUJ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"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于画图克隆 - 捐赠")
        self.setFixedSize(800, 800)
        self.setModal(True)
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("支持画图AI作者 - 捐赠支持1元")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 描述
        description_label = QLabel(
            "感谢您使用画图AI！\n\n"
            "如果您喜欢这个项目并希望支持作者持续开发其他项目，欢迎通过以下方式进行捐赠。\n"
            "您的支持将帮助我们改进功能、修复错误并添加新特性。"
        )
        description_label.setWordWrap(True)
        description_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(description_label)
        
        layout.addSpacing(20)
        
        # 二维码区域
        qr_group = QGroupBox("扫码捐赠")
        qr_layout = QHBoxLayout(qr_group)
        qr_layout.setSpacing(30)
        
        # 微信二维码
        wechat_widget = self.create_qr_widget("微信")
        qr_layout.addWidget(wechat_widget)
        
        # 支付宝二维码
        alipay_widget = self.create_qr_widget("支付宝")
        qr_layout.addWidget(alipay_widget)
        
        layout.addWidget(qr_group)
        
        layout.addSpacing(20)
        
        # 贝宝捐赠按钮
        paypal_label = QLabel("国际用户可通过贝宝(PayPal)捐赠：")
        paypal_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(paypal_label)
        
        paypal_button = QPushButton("前往贝宝捐赠")
        paypal_button.setStyleSheet("""
            QPushButton {{
                background-color: #0070BA;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: #005EA6;
            }}
        """)
        paypal_button.clicked.connect(self.open_paypal)
        layout.addWidget(paypal_button, alignment=Qt.AlignCenter)
        
        layout.addStretch()
        
        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=Qt.AlignCenter)
    
    def create_qr_widget(self, platform):
        """创建二维码显示组件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        
        # 图片标签
        pixmap = QPixmap()
        if platform == "微信":
            base64_str = self.WECHAT_QR_BASE64
        else:
            base64_str = self.ALIPAY_QR_BASE64
        
        try:
            image_data = base64.b64decode(base64_str)
            image = QImage.fromData(image_data)
            if not image.isNull():
                pixmap = QPixmap.fromImage(image)
                # 缩放为300x300正方形，保持比例，完整显示（可能留白）
                pixmap = pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                # 创建300x300的正方形背景
                square_pixmap = QPixmap(300, 300)
                square_pixmap.fill(Qt.transparent)
                painter = QPainter(square_pixmap)
                # 将缩放后的图片绘制在中央
                x = (300 - pixmap.width()) // 2
                y = (300 - pixmap.height()) // 2
                painter.drawPixmap(x, y, pixmap)
                painter.end()
                pixmap = square_pixmap
            else:
                raise ValueError("图像数据无效")
        except Exception:
            # 如果解码失败，创建灰色占位符
            pixmap = QPixmap(300, 300)
            pixmap.fill(QColor(200, 200, 200))
            painter = QPainter(pixmap)
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(pixmap.rect(), Qt.AlignCenter, f"{platform}\n二维码")
            painter.end()
        
        image_label = QLabel()
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(image_label)
        
        # 平台名称
        name_label = QLabel(platform)
        name_label.setStyleSheet("font-weight: bold; margin-top: 10px; font-size: 14px;")
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)
        
        return widget
    
    def open_paypal(self):
        """打开贝宝捐赠链接"""
        import webbrowser
        webbrowser.open("https://www.paypal.com/ncp/payment/FYDUKTJ33DQKW")
        QMessageBox.information(self, "贝宝捐赠", "已打开贝宝捐赠页面，请按页面指示完成捐赠。感谢您的支持！")



class AIGenerateDialog(QDialog):
    """AI生成提示词对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI图像生成")
        self.setFixedSize(500, 600)
        self.setModal(True)
        
        # 获取父窗口的AI设置
        self.parent_window = parent
        self.ai_settings = {}
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 提示词标签
        prompt_label = QLabel("请输入图像生成提示词:")
        prompt_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(prompt_label)
        
        # 提示词输入框
        self.prompt_textedit = QTextEdit()
        self.prompt_textedit.setPlaceholderText("例如：一只可爱的猫咪坐在窗台上，阳光洒进来，温馨的氛围")
        self.prompt_textedit.setMinimumHeight(80)
        self.prompt_textedit.setMaximumHeight(200)
        self.prompt_textedit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #808080;
                border-radius: 3px;
                padding: 5px;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.prompt_textedit)
        
        # 快速提示词按钮
        quick_prompts_group = QGroupBox("快速提示词")
        quick_prompts_layout = QVBoxLayout(quick_prompts_group)
        
        quick_prompts = [
            "风景画：美丽的山水画，夕阳西下，宁静祥和",
            "人物画：年轻女性的肖像，温柔的笑容",
            "动物画：可爱的小狗在草地上奔跑",
            "抽象画：色彩斑斓的几何图形组合",
            "建筑画：现代城市天际线，高楼大厦"
        ]
        
        for prompt in quick_prompts:
            btn = QPushButton(prompt[:20] + "..." if len(prompt) > 20 else prompt)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #E8E5D8;
                    border: 1px solid #808080;
                    padding: 5px;
                    text-align: left;
                    font-size: 13px;
                    min-height: 24px;
                }
                QPushButton:hover {
                    background-color: #D4D0C8;
                }
            """)
            btn.clicked.connect(lambda checked, p=prompt: self.set_prompt(p))
            quick_prompts_layout.addWidget(btn)
        
        layout.addWidget(quick_prompts_group)
        
        # 生成设置
        settings_group = QGroupBox("生成设置")
        settings_layout = QHBoxLayout(settings_group)
        
        # 图像数量
        settings_layout.addWidget(QLabel("数量:"))
        self.n_spin = QSpinBox()
        self.n_spin.setRange(1, 4)
        self.n_spin.setValue(1)
        self.n_spin.setFixedWidth(50)
        settings_layout.addWidget(self.n_spin)
        
        settings_layout.addSpacing(20)
        
        # 超时时间
        settings_layout.addWidget(QLabel("超时:"))
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(30, 300)
        self.timeout_spin.setValue(60)
        self.timeout_spin.setSuffix(" 秒")
        self.timeout_spin.setFixedWidth(80)
        settings_layout.addWidget(self.timeout_spin)
        
        settings_layout.addStretch()
        layout.addWidget(settings_group)
        
        # 进度条（初始隐藏）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #808080;
                border-radius: 3px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #316AC5;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.generate_button = QPushButton("生成")
        self.generate_button.setFixedWidth(80)
        self.generate_button.setStyleSheet("""
            QPushButton {
                background-color: #E8E5D8;
                border: 1px solid #808080;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #D4D0C8;
            }
            QPushButton:pressed {
                background-color: #C0C0C0;
            }
        """)
        self.generate_button.clicked.connect(self.generate_image)
        
        cancel_button = QPushButton("取消")
        cancel_button.setFixedWidth(80)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #E8E5D8;
                border: 1px solid #808080;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #D4D0C8;
            }
            QPushButton:pressed {
                background-color: #C0C0C0;
            }
        """)
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.generate_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # 工作线程
        self.worker_thread = None
        
    def set_prompt(self, prompt):
        """设置提示词"""
        self.prompt_textedit.setPlainText(prompt)
    
    def generate_image(self):
        """生成图像"""
        prompt = self.prompt_textedit.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "提示", "请输入提示词")
            return
        
        # 禁用生成按钮，显示进度条
        self.generate_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定模式
        
        # 从父窗口获取AI设置
        if hasattr(self.parent_window, 'ai_settings'):
            self.ai_settings = self.parent_window.ai_settings
        
        # 创建工作线程,传入设置
        self.worker_thread = AIImageWorker(
            prompt, 
            self.n_spin.value(), 
            self.timeout_spin.value(),
            self.ai_settings
        )
        self.worker_thread.finished.connect(self.on_generation_finished)
        self.worker_thread.error.connect(self.on_generation_error)
        self.worker_thread.start()
    
    def on_generation_finished(self, image_data_list):
        """生成完成"""
        self.progress_bar.setVisible(False)
        self.generate_button.setEnabled(True)
        
        if image_data_list:
            self.generated_images = image_data_list
            self.accept()
        else:
            QMessageBox.warning(self, "错误", "未能生成图像")
    
    def on_generation_error(self, error_msg):
        """生成错误"""
        self.progress_bar.setVisible(False)
        self.generate_button.setEnabled(True)
        QMessageBox.critical(self, "错误", f"图像生成失败: {error_msg}")


class AIImageWorker(QThread):
    """AI图像生成工作线程"""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, prompt, n=1, timeout=60, settings=None):
        super().__init__()
        self.prompt = prompt
        self.n = n
        self.timeout = timeout
        self._is_running = True
        
        # 从设置中加载API配置,如果没有则使用默认值
        if settings is None:
            settings = {}
        
        self.api_key = settings.get('api_key', 'user-modified-api-key-12345')
        self.api_base_url = settings.get('api_base_url', 'https://ark.cn-beijing.volces.com/api/v3')
        self.image_endpoint = settings.get('image_endpoint', '/images/generations')
        self.model_name = settings.get('model_name', 'doubao-seedream-4-5-251128')
        self.image_size = settings.get('image_size', '2048x1800')
        
    def run(self):
        """在工作线程中执行图像生成"""
        try:
            # 调用真实的豆包API
            image_data_list = self.generate_doubao_images()
            
            # 如果还没有超时,发送完成信号
            if self._is_running:
                self.finished.emit(image_data_list)
        except requests.exceptions.Timeout:
            if self._is_running:
                self.error.emit(f"API请求超时({self.timeout}秒),请检查网络连接或增加超时时间")
        except requests.exceptions.RequestException as e:
            if self._is_running:
                self.error.emit(f"网络请求错误: {str(e)}")
        except Exception as e:
            if self._is_running:
                self.error.emit(f"发生错误: {str(e)}")
    
    def generate_doubao_images(self):
        """使用豆包API生成图像"""
        image_data_list = []
        
        # 准备API请求
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # 请求负载
        payload = {
            "model": self.model_name,
            "prompt": self.prompt,
            "n": self.n,
            "size": self.image_size
        }
        
        # 完整的API URL
        api_url = self.api_base_url + self.image_endpoint
        
        # 发起API请求
        response = requests.post(api_url, headers=headers, json=payload, timeout=self.timeout)
        
        if response.status_code == 200:
            result = response.json()
            
            # 从响应中提取图像
            if 'data' in result and len(result['data']) > 0:
                for item in result['data']:
                    # 检查是否有URL
                    if 'url' in item:
                        image_url = item['url']
                        # 下载图像
                        image_response = requests.get(image_url, timeout=self.timeout)
                        image_response.raise_for_status()
                        
                        # 转换为base64
                        image_data = base64.b64encode(image_response.content).decode('utf-8')
                        image_data_list.append(image_data)
                        
                    # 或者检查是否有base64数据
                    elif 'b64_json' in item:
                        image_data_list.append(item['b64_json'])
                
                if not image_data_list:
                    raise ValueError("未从API响应中找到有效的图像数据")
            else:
                raise ValueError("API响应中没有图像数据")
        else:
            error_msg = f"API请求失败: {response.status_code}"
            try:
                error_detail = response.json()
                if 'error' in error_detail:
                    error_msg += f" - {error_detail['error']}"
            except:
                error_msg += f" - {response.text}"
            raise Exception(error_msg)
        
        return image_data_list


class StretchSkewDialog(QDialog):
    """拉伸和扭曲对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("拉伸和扭曲")
        self.setFixedSize(250, 300)
        
        layout = QVBoxLayout(self)
        
        # 拉伸部分
        stretch_group = QGroupBox("拉伸")
        stretch_layout = QFormLayout(stretch_group)
        
        self.horizontal_stretch_spin = QSpinBox()
        self.horizontal_stretch_spin.setRange(1, 500)
        self.horizontal_stretch_spin.setValue(100)
        self.horizontal_stretch_spin.setSuffix(" %")
        stretch_layout.addRow("水平(H)：", self.horizontal_stretch_spin)
        
        self.vertical_stretch_spin = QSpinBox()
        self.vertical_stretch_spin.setRange(1, 500)
        self.vertical_stretch_spin.setValue(100)
        self.vertical_stretch_spin.setSuffix(" %")
        stretch_layout.addRow("垂直(V)：", self.vertical_stretch_spin)
        
        layout.addWidget(stretch_group)
        
        # 扭曲部分
        skew_group = QGroupBox("扭曲")
        skew_layout = QFormLayout(skew_group)
        
        self.horizontal_skew_spin = QSpinBox()
        self.horizontal_skew_spin.setRange(-89, 89)
        self.horizontal_skew_spin.setValue(0)
        self.horizontal_skew_spin.setSuffix(" 度")
        skew_layout.addRow("水平(O)：", self.horizontal_skew_spin)
        
        self.vertical_skew_spin = QSpinBox()
        self.vertical_skew_spin.setRange(-89, 89)
        self.vertical_skew_spin.setValue(0)
        self.vertical_skew_spin.setSuffix(" 度")
        skew_layout.addRow("垂直(E)：", self.vertical_skew_spin)
        
        layout.addWidget(skew_group)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)


class FlipRotateDialog(QDialog):
    """翻转和旋转对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("翻转和旋转")
        self.setFixedSize(300, 300)
        
        layout = QVBoxLayout(self)
        
        # 选项组
        options_group = QGroupBox("翻转或旋转")
        options_layout = QVBoxLayout(options_group)
        
        self.flip_horizontal_radio = QRadioButton("水平翻转 (F)")
        self.flip_vertical_radio = QRadioButton("垂直翻转 (V)")
        self.rotate_radio = QRadioButton("按一定角度旋转 (R)")
        self.rotate_radio.setChecked(True)
        
        options_layout.addWidget(self.flip_horizontal_radio)
        options_layout.addWidget(self.flip_vertical_radio)
        options_layout.addWidget(self.rotate_radio)
        
        layout.addWidget(options_group)
        
        # 旋转角度组
        angle_group = QGroupBox()
        angle_layout = QVBoxLayout(angle_group)
        
        self.rotate_90_radio = QRadioButton("90 度 (9)")
        self.rotate_180_radio = QRadioButton("180 度 (1)")
        self.rotate_270_radio = QRadioButton("270 度 (2)")
        self.rotate_90_radio.setChecked(True)
        
        angle_layout.addWidget(self.rotate_90_radio)
        angle_layout.addWidget(self.rotate_180_radio)
        angle_layout.addWidget(self.rotate_270_radio)
        
        layout.addWidget(angle_group)
        
        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
    
    def get_selection(self):
        """获取用户选择"""
        if self.flip_horizontal_radio.isChecked():
            return "horizontal"
        elif self.flip_vertical_radio.isChecked():
            return "vertical"
        elif self.rotate_radio.isChecked():
            if self.rotate_90_radio.isChecked():
                return "rotate_90"
            elif self.rotate_180_radio.isChecked():
                return "rotate_180"
            elif self.rotate_270_radio.isChecked():
                return "rotate_270"
        return "rotate_90"


class TextInputWidget(QLineEdit):
    """增强的文字输入框 - 更稳定可靠"""
    returnPressed = pyqtSignal()  # 保持与原版的兼容性
    selection_font_changed = pyqtSignal(QFont)  # 字体变化信号
    
    def __init__(self, parent=None, canvas_pos=None):
        super().__init__(parent)
        self.canvas_pos = canvas_pos or QPoint()
        self.setMinimumSize(100, 25)
        self.dragging = False
        self.drag_start_pos = QPoint()
        
        # 简洁实用的样式
        self.setStyleSheet("""
            QLineEdit {
                border: 2px solid #316AC5;
                border-radius: 3px;
                background-color: transparent;
                padding: 4px;
                selection-background-color: #316AC5;
                selection-color: white;
            }
            QLineEdit:focus {
                border-color: #316AC5;
                outline: none;
            }
        """)
        
        self.setFocusPolicy(Qt.StrongFocus)
        self.textChanged.connect(self.on_text_changed)
        
    def on_text_changed(self):
        """文字变化时发送字体信号"""
        self.selection_font_changed.emit(self.font())
        
    def focusInEvent(self, event):
        """获取焦点时同步字体"""
        super().focusInEvent(event)
        self.selection_font_changed.emit(self.font())
        
    def setFont(self, font):
        """设置字体并自动调整大小 - 修复大字号问题"""
        # 设置新字体
        super().setFont(font)
        
        # 获取字体度量
        metrics = self.fontMetrics()
        text_height = metrics.height()
        
        # 获取当前字号，用于比例计算
        font_size = font.pointSize()
        if font_size <= 0:
            font_size = 12  # 默认值
            
        # 计算新尺寸 - 基于字号的动态计算
        current_text = self.text()
        if current_text:
            text_width = metrics.width(current_text)
            # 基础宽度 + 文字宽度 + 字号比例调整
            base_width = 120
            width_scale = max(1.0, font_size / 12.0)  # 12号字为基准
            new_width = max(base_width * width_scale, text_width + 30)
        else:
            # 空文字时的默认宽度，基于字号
            base_width = 120
            width_scale = max(1.0, font_size / 12.0)
            new_width = base_width * width_scale
            
        # 高度计算 - 基于字号的动态计算
        base_height = 30
        height_scale = max(1.0, font_size / 12.0)
        new_height = max(base_height * height_scale, text_height + 12)
        
        # 确保最小尺寸合理
        new_width = max(new_width, 80)
        new_height = max(new_height, 30)
        
        # 确保最大尺寸不超过合理范围
        new_width = min(new_width, 800)  # 最大800像素
        new_height = min(new_height, 200)  # 最大200像素
        
        # 应用新尺寸
        self.setFixedSize(int(new_width), int(new_height))
        
        # 强制立即重绘
        self.update()
        self.repaint()
        
    def keyPressEvent(self, event):
        """键盘事件 - 简化处理"""
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Escape):
            self.returnPressed.emit()
        else:
            super().keyPressEvent(event)
    
    def mousePressEvent(self, event):
        """鼠标按下事件 - 添加拖动支持"""
        if event.button() == Qt.LeftButton:
            # 检查是否点击在边框区域（用于拖动）
            margin = 8
            in_border = (event.pos().x() < margin or
                        event.pos().x() > self.width() - margin or
                        event.pos().y() < margin or
                        event.pos().y() > self.height() - margin)
            
            if in_border:
                # 开始拖动
                self.dragging = True
                self.drag_start_pos = event.pos()
                self.setCursor(Qt.SizeAllCursor)
                event.accept()
                return
        
        # 在内容区域，正常处理文字输入
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 拖动支持"""
        if self.dragging and (event.buttons() & Qt.LeftButton):
            # 拖动模式
            delta = event.pos() - self.drag_start_pos
            new_pos = self.pos() + delta
            self.move(new_pos)
            self.canvas_pos = new_pos
            
            # 通知父窗口位置变化
            if self.parent() and hasattr(self.parent(), 'on_text_input_moved'):
                self.parent().on_text_input_moved(new_pos)
                
            event.accept()
        elif not (event.buttons() & Qt.LeftButton):
            # 鼠标悬停时，根据位置改变光标
            margin = 8
            in_border = (event.pos().x() < margin or
                        event.pos().x() > self.width() - margin or
                        event.pos().y() < margin or
                        event.pos().y() > self.height() - margin)
            
            if in_border:
                self.setCursor(Qt.SizeAllCursor)  # 边框区域显示移动光标
            else:
                self.unsetCursor()  # 内容区域恢复默认光标
                
            super().mouseMoveEvent(event)
        else:
            super().mouseMoveEvent(event)
            
    def mouseReleaseEvent(self, event):
        """鼠标释放事件 - 拖动支持"""
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            self.unsetCursor()
            event.accept()
        else:
            super().mouseReleaseEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开时恢复光标"""
        if not self.dragging:
            self.unsetCursor()
        super().leaveEvent(event)


class TextToolDialog(QDialog):
    """文字工具对话框 - 简化和增强版"""
    font_changed = pyqtSignal(QFont)  # 保持兼容性
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("文字工具栏")
        self.setFixedSize(480, 140)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        self.setup_ui()
        self.connect_signals()
        
    def connect_signals(self):
        """连接信号"""
        self.font_combo.currentTextChanged.connect(self.on_font_changed)
        self.size_combo.currentTextChanged.connect(self.on_font_changed)
        self.bold_btn.toggled.connect(self.on_font_changed)
        self.italic_btn.toggled.connect(self.on_font_changed)
        self.underline_btn.toggled.connect(self.on_font_changed)
        
    def setup_ui(self):
        """设置界面 - 简化版"""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 字体选择区域
        font_widget = QWidget()
        font_layout = QHBoxLayout(font_widget)
        font_layout.setSpacing(8)
        
        self.font_combo = QComboBox()
        font_database = QFontDatabase()
        self.font_combo.addItems(font_database.families())
        default_font = QFont()
        self.font_combo.setCurrentText(default_font.family())
        self.font_combo.setFixedHeight(28)
        self.font_combo.setStyleSheet("""
            QComboBox {
                font-size: 12px;
                padding: 3px;
                border: 1px solid #808080;
                border-radius: 3px;
                background-color: white;
                min-width: 160px;
            }
            QComboBox:hover {
                border-color: #000000;
            }
        """)
        
        self.size_combo = QComboBox()
        self.size_combo.addItems(["8", "9", "10", "11", "12", "14", "16", "18", "20", "22", "24", "28", "32", "36", "48", "72"])
        self.size_combo.setCurrentText("12")
        self.size_combo.setFixedHeight(28)
        self.size_combo.setFixedWidth(70)
        self.size_combo.setStyleSheet("""
            QComboBox {
                font-size: 12px;
                padding: 3px;
                border: 1px solid #808080;
                border-radius: 3px;
                background-color: white;
            }
            QComboBox:hover {
                border-color: #000000;
            }
        """)
        
        font_layout.addWidget(self.font_combo)
        font_layout.addWidget(self.size_combo)
        font_layout.addStretch()
        
        layout.addWidget(font_widget)
        
        # 按钮区域
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setSpacing(6)
        
        self.bold_btn = QPushButton("B")
        self.bold_btn.setCheckable(True)
        self.bold_btn.setFixedSize(32, 28)
        self.bold_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                font-weight: bold;
                background-color: #E0E0E0;
                border: 1px solid #808080;
                border-radius: 3px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #D0D0D0;
                border-color: #000000;
            }
            QPushButton:pressed, QPushButton:checked {
                background-color: #C0C0C0;
                border: 1px inset #606060;
            }
        """)
        
        self.italic_btn = QPushButton("I")
        self.italic_btn.setCheckable(True)
        self.italic_btn.setFixedSize(32, 28)
        self.italic_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                font-style: italic;
                background-color: #E0E0E0;
                border: 1px solid #808080;
                border-radius: 3px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #D0D0D0;
                border-color: #000000;
            }
            QPushButton:pressed, QPushButton:checked {
                background-color: #C0C0C0;
                border: 1px inset #606060;
            }
        """)
        
        self.underline_btn = QPushButton("U")
        self.underline_btn.setCheckable(True)
        self.underline_btn.setFixedSize(32, 28)
        self.underline_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                text-decoration: underline;
                background-color: #E0E0E0;
                border: 1px solid #808080;
                border-radius: 3px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #D0D0D0;
                border-color: #000000;
            }
            QPushButton:pressed, QPushButton:checked {
                background-color: #C0C0C0;
                border: 1px inset #606060;
            }
        """)
        
        button_layout.addWidget(self.bold_btn)
        button_layout.addWidget(self.italic_btn)
        button_layout.addWidget(self.underline_btn)
        button_layout.addStretch()
        
        layout.addWidget(button_widget)
        
        # 连接信号
        self.font_combo.currentTextChanged.connect(self.on_font_changed)
        self.size_combo.currentTextChanged.connect(self.on_font_changed)
        self.bold_btn.toggled.connect(self.on_font_changed)
        self.italic_btn.toggled.connect(self.on_font_changed)
        self.underline_btn.toggled.connect(self.on_font_changed)
        
        # 设置整体样式
        self.setStyleSheet("""
            QDialog {
                background-color: #F0F0F0;
                border: 2px solid #808080;
                border-radius: 0px;
            }
            QPushButton {
                background-color: #E0E0E0;
                border: 1px solid #808080;
                border-radius: 3px;
                font-size: 12px;
                padding: 2px;
                min-width: 32px;
                min-height: 28px;
            }
            QPushButton:hover {
                background-color: #D0D0D0;
                border-color: #000000;
            }
            QPushButton:pressed, QPushButton:checked {
                background-color: #C0C0C0;
                border: 1px inset #606060;
            }
        """)
    
    def get_font(self):
        """获取选中的字体 - 增强版"""
        # 获取字号，确保是有效的数字
        try:
            size_text = self.size_combo.currentText()
            font_size = int(size_text)
        except (ValueError, TypeError):
            font_size = 12  # 默认值
            
        # 创建字体对象
        font = QFont(self.font_combo.currentText(), font_size)
        font.setBold(self.bold_btn.isChecked())
        font.setItalic(self.italic_btn.isChecked())
        font.setUnderline(self.underline_btn.isChecked())
        
        # 确保字号设置正确
        if font.pointSize() != font_size:
            font.setPointSize(font_size)
            
        return font
        
    def set_font_from_widget(self, font):
        """从文字输入框同步字体状态 - 增强版"""
        # 阻止信号触发，避免循环
        self.font_combo.blockSignals(True)
        self.size_combo.blockSignals(True)
        self.bold_btn.blockSignals(True)
        self.italic_btn.blockSignals(True)
        self.underline_btn.blockSignals(True)
        
        # 更新工具栏状态
        self.font_combo.setCurrentText(font.family())
        
        # 确保字号正确设置
        font_size = font.pointSize()
        if font_size > 0:
            self.size_combo.setCurrentText(str(font_size))
        else:
            # 如果pointSize无效，尝试pixelSize转换
            pixel_size = font.pixelSize()
            if pixel_size > 0:
                # 粗略转换：假设1pt ≈ 1.33px
                approx_point_size = max(8, min(72, int(pixel_size / 1.33)))
                self.size_combo.setCurrentText(str(approx_point_size))
            else:
                self.size_combo.setCurrentText("12")  # 默认值
                
        self.bold_btn.setChecked(font.bold())
        self.italic_btn.setChecked(font.italic())
        self.underline_btn.setChecked(font.underline())
        
        # 恢复信号
        self.font_combo.blockSignals(False)
        self.size_combo.blockSignals(False)
        self.bold_btn.blockSignals(False)
        self.italic_btn.blockSignals(False)
        self.underline_btn.blockSignals(False)
        
    def on_font_changed(self):
        """字体变化时的处理 - 增强焦点管理"""
        current_font = self.get_font()
        # 确保总是发出字体变化信号，即使在set_font_from_widget中
        self.font_changed.emit(current_font)
        
        # 强制立即处理信号，避免延迟
        QApplication.processEvents()
        
        # 确保对话框保持激活状态，但不抢夺焦点
        if self.isActiveWindow():
            # 如果对话框是激活的，确保不抢夺输入框焦点
            # 让父窗口处理焦点管理
            if self.parent() and hasattr(self.parent(), 'text_input_widget'):
                parent = self.parent()
                if parent.text_input_widget and parent.text_input_widget.isVisible():
                    # 延迟一点点时间再设置焦点，避免抢夺
                    # 不再将焦点设置回文字输入框，避免干扰用户操作
                    pass


class PaintCanvas(QWidget):
    """画布组件"""
    def __init__(self):
        super().__init__()
        self.setFixedSize(720, 520)
        self.setStyleSheet("background-color: white;")
        self.image = QPixmap(self.size())
        self.image.fill(Qt.white)
        
        self.drawing = False
        self.last_point = QPoint()
        self.start_point = QPoint()
        self.pen_color = QColor(0, 0, 0)
        self.bg_color = QColor(255, 255, 255)
        self.pen_width = 2
        self.pen_style = Qt.SolidLine
        
        # 当前工具
        self.current_tool = "pencil"
        self.temp_image = None
        
        # 文字工具相关
        self.text_tool_dialog = None
        self.text_input_widget = None  # 文字输入框
        self.text_start_point = None
        self.text_content = ""
        self.text_font = QFont("Fixesys", 12)
        self.is_text_mode = False
        
        # 喷枪定时器
        self.airbrush_timer = QTimer()
        self.airbrush_timer.timeout.connect(self.spray_paint)
        self.current_spray_pos = QPoint()
        
        # 选区相关
        self.selection_rect = QRect()
        self.selection_active = False
        self.selection_dragging = False
        self.selection_content = None  # 选区内容的图像副本
        self.selection_transform_mode = None  # "move", "resize", "rotate"
        self.selection_start_pos = QPoint()  # 选区操作起始位置
        
        # 任意形状选区相关
        self.crop_points = []  # 任意形状选区的顶点
        self.crop_drawing = False  # 是否正在绘制选区
        self.crop_selection_active = False  # 任意形状选区是否激活
        self.crop_selection_content = None  # 任意形状选区内容的图像副本
        self.crop_selection_mask = None  # 任意形状选区掩码
        self.crop_selection_rect = QRect()  # 任意形状选区的边界矩形
        self.crop_selection_offset = QPoint(0, 0)  # 选区内容相对于原始位置的偏移
        self.crop_selection_original_points = []  # 选区的原始顶点（用于移动时更新）
        self.crop_selection_dragging = False  # 是否正在拖动选区
        
        # 多边形绘制相关
        self.polygon_points = []  # 多边形顶点
        self.polygon_drawing = False  # 多边形绘制状态
        self.polygon_preview = None  # 多边形预览图像
        self.polygon_fill_mode = "outline"  # 多边形填充模式: "outline"(仅轮廓), "filled"(轮廓+填充), "fill_only"(仅填充)
        self._last_polygon_click_time = 0  # 用于检测双击
        self._last_mouse_pos = QPoint()  # 记录鼠标位置用于预览
        
        # 曲线绘制相关
        self.curve_points = []  # 曲线控制点
        self.curve_drawing = False  # 曲线绘制状态
        self._last_curve_click_time = 0  # 用于检测双击
        self.curve_button = None  # 记录使用的鼠标按钮（左键或右键）
        
        # 形状填充模式
        self.shape_fill_mode = "outline"  # "outline"(仅边框), "filled"(边框+填充), "fill_only"(仅填充)
        
        # 画布调整大小相关
        self.resizing_mode = None  # "right", "bottom", "corner"
        self.resizing_start_pos = QPoint()
        self.original_size = QSize()
        self.resize_handle_size = 8  # 控制点大小
        self.original_image = None  # 原始图像副本，用于调整大小
        
        # 缩放（放大镜工具，仅影响显示，不改变画布内容）
        self.zoom_factor = 1.0       # 当前缩放倍率
        self.zoom_levels = [0.2, 0.25, 1/3, 0.5, 1.0, 2.0, 3.0]  # 可用档位
        self.zoom_index = 4          # 默认1.0在第4位

        # 撤销/重做系统
        self.undo_stack = []  # 撤销栈，存储QPixmap的深拷贝
        self.redo_stack = []  # 重做栈
        self.max_history = 5  # 最大历史记录数
        
        # 画布内容变化跟踪
        self.content_modified = False
        self.original_content_hash = self._calculate_image_hash()
        
    def _calculate_image_hash(self):
        """计算当前图像的哈希值用于检测变化"""
        try:
            # 将QPixmap转换为QImage以便获取像素数据
            image = self.image.toImage()
            # 获取图像数据的字节表示
            bits = image.bits()
            bits.setsize(image.byteCount())
            # 计算哈希值
            import hashlib
            return hashlib.md5(bits.tobytes()).hexdigest()
        except:
            return ""
    
    # ── 缩放辅助 ──────────────────────────────────────────────────
    def _apply_zoom(self):
        """根据当前 zoom_factor 调整 widget 的显示尺寸"""
        w = int(self.image.width()  * self.zoom_factor)
        h = int(self.image.height() * self.zoom_factor)
        self.setFixedSize(w, h)
        self.update()

    def zoom_in(self, center=None):
        """放大一档（最大3.0倍），center 为图像坐标点"""
        if self.zoom_index < len(self.zoom_levels) - 1:
            self.zoom_index += 1
            self.zoom_factor = self.zoom_levels[self.zoom_index]
            self._apply_zoom()
            self._update_zoom_status()

    def zoom_out(self, center=None):
        """缩小一档（最小0.2倍），center 为图像坐标点"""
        if self.zoom_index > 0:
            self.zoom_index -= 1
            self.zoom_factor = self.zoom_levels[self.zoom_index]
            self._apply_zoom()
            self._update_zoom_status()

    def reset_zoom(self):
        """还原为100%"""
        self.zoom_index = 4
        self.zoom_factor = 1.0
        self._apply_zoom()
        self._update_zoom_status()

    def _update_zoom_status(self):
        """向父窗口状态栏推送缩放信息"""
        try:
            pct = int(round(self.zoom_factor * 100))
            self.parent().statusBar().showMessage(f"缩放: {pct}%")
        except Exception:
            pass

    def _widget_to_image(self, pos):
        """把 widget 坐标转换为图像坐标"""
        if self.zoom_factor == 1.0:
            return pos
        x = int(pos.x() / self.zoom_factor)
        y = int(pos.y() / self.zoom_factor)
        return QPoint(x, y)

    # ── 撤销/重做 ────────────────────────────────────────────────
    def save_state(self):
        """在操作执行前调用，将当前画布状态推入撤销栈"""
        # 创建当前图像的深拷贝（操作前的快照）
        image_copy = QPixmap(self.image)
        
        # 添加到撤销栈
        self.undo_stack.append(image_copy)
        
        # 限制历史记录数量
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
        
        # 每次新操作前清空重做栈（新操作会使重做历史失效）
        self.redo_stack.clear()
    
    def undo(self):
        """撤销操作"""
        if not self.undo_stack:
            return False
        
        # 将当前状态保存到重做栈
        current_image = QPixmap(self.image)
        self.redo_stack.append(current_image)
        
        # 从撤销栈恢复上一个状态
        prev_image = self.undo_stack.pop()
        self.image = QPixmap(prev_image)
        
        self.update()
        self.mark_content_modified()
        return True
    
    def redo(self):
        """重做操作"""
        if not self.redo_stack:
            return False
        
        # 将当前状态保存到撤销栈
        current_image = QPixmap(self.image)
        self.undo_stack.append(current_image)
        
        # 从重做栈恢复下一个状态
        next_image = self.redo_stack.pop()
        self.image = QPixmap(next_image)
        
        self.update()
        self.mark_content_modified()
        return True

    def mark_content_modified(self):
        """标记画布内容为已修改"""
        self.content_modified = True
        
    def is_content_modified(self):
        """检查画布内容是否已修改"""
        if not self.content_modified:
            # 如果还没有标记为修改，检查当前图像哈希值是否与原始哈希值不同
            current_hash = self._calculate_image_hash()
            if current_hash != self.original_content_hash:
                self.content_modified = True
        return self.content_modified
    
    def reset_content_modified_flag(self):
        """重置内容修改标志（通常在保存后调用）"""
        self.content_modified = False
        self.original_content_hash = self._calculate_image_hash()
    
    def perform_crop_operation(self):
        """执行任意形状裁剪操作"""
        if len(self.crop_points) >= 3:
            # 创建裁剪后的新图像
            image = self.image.toImage()
            
            # 计算多边形的边界矩形
            min_x = min(point.x() for point in self.crop_points)
            max_x = max(point.x() for point in self.crop_points)
            min_y = min(point.y() for point in self.crop_points)
            max_y = max(point.y() for point in self.crop_points)
            
            # 创建新的图像，用背景色填充
            new_image = QImage(max_x - min_x, max_y - min_y, QImage.Format_ARGB32)
            new_image.fill(self.bg_color)
            
            # 创建多边形路径
            path = QPainterPath()
            if self.crop_points:
                path.moveTo(self.crop_points[0].x() - min_x, self.crop_points[0].y() - min_y)
                for point in self.crop_points[1:]:
                    path.lineTo(point.x() - min_x, point.y() - min_y)
                path.closeSubpath()
            
            # 在新图像上绘制裁剪区域的内容
            painter = QPainter(new_image)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setClipPath(path)
            painter.drawImage(0, 0, image, min_x, min_y, max_x - min_x, max_y - min_y)
            painter.end()
            
            # 更新画布图像
            self.image = QPixmap.fromImage(new_image)
            # 调整画布组件尺寸以匹配新图像大小（保持当前缩放）
            self._apply_zoom()
            self.mark_content_modified()
        
        # 清除裁剪状态
        self.crop_points = []
        self.update()
    
    def finish_polygon(self):
        """完成多边形绘制（对标微软画图）"""
        if len(self.polygon_points) < 3:
            # 顶点太少，取消绘制
            self.cancel_polygon()
            return
        
        painter = QPainter(self.image)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 根据最后使用的鼠标按钮确定颜色
        draw_color = self.pen_color if getattr(self, 'last_button', Qt.LeftButton) == Qt.LeftButton else self.bg_color
        
        # 根据填充模式绘制多边形
        if self.polygon_fill_mode == "outline":
            # 仅轮廓
            painter.setPen(QPen(draw_color, self.pen_width, self.pen_style, Qt.RoundCap, Qt.RoundJoin))
            painter.setBrush(Qt.NoBrush)
        elif self.polygon_fill_mode == "filled":
            # 轮廓+填充（轮廓用前景色，填充用背景色）
            painter.setPen(QPen(draw_color, self.pen_width, self.pen_style, Qt.RoundCap, Qt.RoundJoin))
            painter.setBrush(QBrush(self.bg_color))
        else:  # "fill_only"
            # 仅填充，无轮廓
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(draw_color))
        
        # 使用QPolygon绘制闭合多边形
        from PyQt5.QtGui import QPolygon
        polygon = QPolygon(self.polygon_points)
        painter.drawPolygon(polygon)
        painter.end()
        
        self.mark_content_modified()
        
        # 清除多边形绘制状态
        self.polygon_drawing = False
        self.polygon_points = []
        self.polygon_preview = None
        self.temp_image = None
        self._last_polygon_click_time = 0
        self.update()
    
    def cancel_polygon(self):
        """取消多边形绘制"""
        self.polygon_drawing = False
        self.polygon_points = []
        self.polygon_preview = None
        if self.temp_image:
            self.image = self.temp_image.copy()
        self.update()
    
    def catmull_rom_spline(self, p0, p1, p2, p3, num_points=20):
        """
        计算Catmull-Rom样条曲线上的点
        p0, p1, p2, p3: 四个控制点 (QPoint)
        num_points: 在p1和p2之间生成的点数
        返回: 点的列表
        """
        points = []
        for i in range(num_points + 1):
            t = i / num_points
            t2 = t * t
            t3 = t2 * t
            
            # Catmull-Rom 样条公式
            x = 0.5 * (
                (2 * p1.x()) +
                (-p0.x() + p2.x()) * t +
                (2*p0.x() - 5*p1.x() + 4*p2.x() - p3.x()) * t2 +
                (-p0.x() + 3*p1.x() - 3*p2.x() + p3.x()) * t3
            )
            y = 0.5 * (
                (2 * p1.y()) +
                (-p0.y() + p2.y()) * t +
                (2*p0.y() - 5*p1.y() + 4*p2.y() - p3.y()) * t2 +
                (-p0.y() + 3*p1.y() - 3*p2.y() + p3.y()) * t3
            )
            points.append(QPoint(int(x), int(y)))
        
        return points
    
    def draw_catmull_rom_curve(self, points, painter=None):
        """
        绘制完整的Catmull-Rom样条曲线
        points: 控制点列表
        painter: 如果提供，使用此painter，否则在self.image上绘制
        """
        if len(points) < 2:
            return
        
        should_end = False
        if painter is None:
            painter = QPainter(self.image)
            painter.setRenderHint(QPainter.Antialiasing)
            should_end = True
        
        # 根据鼠标按钮确定颜色
        draw_color = self.pen_color if self.curve_button == Qt.LeftButton else self.bg_color
        painter.setPen(QPen(draw_color, self.pen_width, self.pen_style, Qt.RoundCap, Qt.RoundJoin))
        
        if len(points) == 2:
            # 只有两个点，绘制直线
            painter.drawLine(points[0], points[1])
        elif len(points) == 3:
            # 三个点，使用第一个点作为虚拟起点
            curve_points = self.catmull_rom_spline(points[0], points[0], points[1], points[2])
            for i in range(len(curve_points) - 1):
                painter.drawLine(curve_points[i], curve_points[i + 1])
            curve_points = self.catmull_rom_spline(points[0], points[1], points[2], points[2])
            for i in range(len(curve_points) - 1):
                painter.drawLine(curve_points[i], curve_points[i + 1])
        else:
            # 四个或更多点，绘制完整的Catmull-Rom样条
            # 第一段：使用第一个点作为虚拟起点
            curve_points = self.catmull_rom_spline(points[0], points[0], points[1], points[2])
            for i in range(len(curve_points) - 1):
                painter.drawLine(curve_points[i], curve_points[i + 1])
            
            # 中间段
            for i in range(len(points) - 3):
                curve_points = self.catmull_rom_spline(points[i], points[i+1], points[i+2], points[i+3])
                for j in range(len(curve_points) - 1):
                    painter.drawLine(curve_points[j], curve_points[j + 1])
            
            # 最后一段：使用最后一个点作为虚拟终点
            curve_points = self.catmull_rom_spline(points[-3], points[-2], points[-1], points[-1])
            for i in range(len(curve_points) - 1):
                painter.drawLine(curve_points[i], curve_points[i + 1])
        
        if should_end:
            painter.end()
    
    def finish_curve(self):
        """完成曲线绘制"""
        if len(self.curve_points) < 2:
            # 点太少，取消绘制
            self.cancel_curve()
            return
        
        # 在画布上绘制最终曲线
        self.draw_catmull_rom_curve(self.curve_points)
        self.mark_content_modified()
        
        # 清除曲线绘制状态
        self.curve_drawing = False
        self.curve_points = []
        self.curve_button = None
        self._last_curve_click_time = 0
        self.temp_image = None
        self.update()
    
    def cancel_curve(self):
        """取消曲线绘制"""
        self.curve_drawing = False
        self.curve_points = []
        self.curve_button = None
        self._last_curve_click_time = 0
        if self.temp_image:
            self.image = self.temp_image.copy()
        self.update()
    
    def capture_selection_content(self):
        """捕获选区内容"""
        if self.selection_active and not self.selection_rect.isEmpty():
            # 捕获选区内的图像内容
            self.selection_content = self.image.copy(self.selection_rect)
            # 在原始图像上清空选区区域（用背景色填充）
            painter = QPainter(self.image)
            painter.setPen(Qt.NoPen)
            painter.setBrush(self.bg_color)
            painter.drawRect(self.selection_rect)
            painter.end()
    
    def commit_selection(self):
        """提交选区内容到画布"""
        if self.selection_active and self.selection_content is not None:
            # 将选区内容绘制回画布
            painter = QPainter(self.image)
            painter.drawPixmap(self.selection_rect.topLeft(), self.selection_content)
            painter.end()
            self.mark_content_modified()
        
        # 清除选区
        self.clear_selection()
    
    def clear_selection(self):
        """清除选区"""
        self.selection_active = False
        self.selection_rect = QRect()
        self.selection_content = None
        self.selection_transform_mode = None
        self.update()
    
    def is_point_in_selection(self, pos):
        """检查点是否在选区内"""
        return self.selection_active and self.selection_rect.contains(pos)
    
    def capture_crop_selection_content(self):
        """捕获任意形状选区内容"""
        if len(self.crop_points) >= 3:
            # 计算多边形的边界矩形
            min_x = min(point.x() for point in self.crop_points)
            max_x = max(point.x() for point in self.crop_points)
            min_y = min(point.y() for point in self.crop_points)
            max_y = max(point.y() for point in self.crop_points)
            
            # 确保边界在画布范围内
            min_x = max(0, min_x)
            min_y = max(0, min_y)
            max_x = min(self.image.width(), max_x)
            max_y = min(self.image.height(), max_y)
            
            width = max_x - min_x
            height = max_y - min_y
            
            if width <= 0 or height <= 0:
                return
            
            # 保存原始边界矩形
            self.crop_selection_rect = QRect(min_x, min_y, width, height)
            
            # 保存原始顶点位置（相对于边界矩形左上角）
            self.crop_selection_original_points = [
                QPoint(p.x() - min_x, p.y() - min_y) for p in self.crop_points
            ]
            
            # 创建选区内容图像（带透明背景）
            content_image = QImage(width, height, QImage.Format_ARGB32)
            content_image.fill(Qt.transparent)
            
            # 创建多边形路径（相对于边界矩形）
            path = QPainterPath()
            if self.crop_points:
                path.moveTo(self.crop_points[0].x() - min_x, self.crop_points[0].y() - min_y)
                for point in self.crop_points[1:]:
                    path.lineTo(point.x() - min_x, point.y() - min_y)
                path.closeSubpath()
            
            # 在内容图像上绘制裁剪区域的内容
            source_image = self.image.toImage()
            painter = QPainter(content_image)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setClipPath(path)
            painter.drawImage(0, 0, source_image, min_x, min_y, width, height)
            painter.end()
            
            # 保存选区内容
            self.crop_selection_content = QPixmap.fromImage(content_image)
            self.crop_selection_mask = path
            
            # 在原始图像上用背景色填充选区区域
            painter = QPainter(self.image)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(self.bg_color)
            
            # 创建原始位置的路径
            original_path = QPainterPath()
            if self.crop_points:
                original_path.moveTo(self.crop_points[0])
                for point in self.crop_points[1:]:
                    original_path.lineTo(point)
                original_path.closeSubpath()
            painter.drawPath(original_path)
            painter.end()
            
            # 重置偏移量
            self.crop_selection_offset = QPoint(0, 0)
            self.crop_selection_active = True
            self.mark_content_modified()
    
    def commit_crop_selection(self):
        """提交任意形状选区内容到画布"""
        if self.crop_selection_active and self.crop_selection_content is not None:
            # 计算当前选区位置
            current_rect = self.crop_selection_rect.translated(self.crop_selection_offset)
            
            # 将选区内容绘制回画布
            painter = QPainter(self.image)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.drawPixmap(current_rect.topLeft(), self.crop_selection_content)
            painter.end()
            self.mark_content_modified()
        
        # 清除选区
        self.clear_crop_selection()
    
    def clear_crop_selection(self):
        """清除任意形状选区"""
        self.crop_selection_active = False
        self.crop_selection_content = None
        self.crop_selection_mask = None
        self.crop_selection_rect = QRect()
        self.crop_selection_offset = QPoint(0, 0)
        self.crop_selection_original_points = []
        self.crop_selection_dragging = False
        self.crop_points = []
        self.crop_drawing = False
        self.update()
    
    def is_point_in_crop_selection(self, pos):
        """检查点是否在任意形状选区内"""
        if not self.crop_selection_active:
            return False
        
        # 计算当前选区的边界矩形
        current_rect = self.crop_selection_rect.translated(self.crop_selection_offset)
        
        # 如果没有mask（如粘贴后），使用边界矩形判断
        # 这样即使没有 crop_selection_mask（如粘贴后），也能正常拖动
        if self.crop_selection_mask is None:
            return current_rect.contains(pos)
        
        # 首先检查是否在边界矩形内
        if not current_rect.contains(pos):
            return False
        
        # 检查是否在多边形路径内（需要转换到选区本地坐标系）
        local_pos = pos - current_rect.topLeft()
        return self.crop_selection_mask.contains(local_pos)
    def copy_selection(self):
        """复制选区内容到剪贴板"""
        clipboard = QApplication.clipboard()
        mime_data = QMimeData()
        
        # 首先检查任意形状选区
        if self.crop_selection_active and self.crop_selection_content is not None:
            # 保存任意形状选区内容和形状信息
            mime_data.setImageData(self.crop_selection_content.toImage())
            
            # 保存选区类型和形状数据
            shape_data = {
                'type': 'crop',
                'points': [(p.x(), p.y()) for p in self.crop_points],
                'original_points': [(p.x(), p.y()) for p in self.crop_selection_original_points] if hasattr(self, 'crop_selection_original_points') else [],
                'offset': (self.crop_selection_offset.x(), self.crop_selection_offset.y())
            }
            mime_data.setData('application/x-custom-selection-shape', json.dumps(shape_data).encode())
            
            clipboard.setMimeData(mime_data)
            return True
        
        # 然后检查矩形选区
        if self.selection_active and self.selection_content is not None:
            # 保存矩形选区内容
            mime_data.setImageData(self.selection_content.toImage())
            
            # 保存选区类型和矩形信息
            shape_data = {
                'type': 'rect',
                'rect': (self.selection_rect.x(), self.selection_rect.y(),
                        self.selection_rect.width(), self.selection_rect.height())
            }
            mime_data.setData('application/x-custom-selection-shape', json.dumps(shape_data).encode())
            
            clipboard.setMimeData(mime_data)
            return True
        
        return False
    def cut_selection(self):
        """剪切选区内容到剪贴板"""
        # 首先检查任意形状选区
        if self.crop_selection_active and self.crop_selection_content is not None:
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(self.crop_selection_content)
            # 清除选区（背景已经在捕获时填充）
            self.clear_crop_selection()
            self.mark_content_modified()
            return True
        # 然后检查矩形选区
        if self.copy_selection():
            # 清空选区区域
            if self.selection_active:
                painter = QPainter(self.image)
                painter.setPen(Qt.NoPen)
                painter.setBrush(self.bg_color)
                painter.drawRect(self.selection_rect)
                painter.end()
                self.mark_content_modified()
                self.clear_selection()
            return True
        return False
    
    def paste_from_clipboard(self):
        """从剪贴板粘贴内容"""
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        
        if not mime_data:
            return False
            
        # 检查是否有自定义选区形状数据
        shape_data_bytes = mime_data.data('application/x-custom-selection-shape')
        has_custom_shape = shape_data_bytes and len(shape_data_bytes) > 0
        
        if has_custom_shape:
            try:
                # 解析选区形状数据
                shape_data = json.loads(shape_data_bytes.data().decode())
                selection_type = shape_data.get('type', 'rect')
                
                # 获取图像数据
                if mime_data.hasImage():
                    image = mime_data.imageData()
                    pixmap = QPixmap.fromImage(image)
                else:
                    pixmap = clipboard.pixmap()
                    
                if pixmap.isNull():
                    return False
                    
                # 如果有当前矩形选区，先提交
                if self.selection_active:
                    self.commit_selection()
                
                # 如果有当前任意形状选区，先提交
                if self.crop_selection_active:
                    self.commit_crop_selection()
                
                if selection_type == 'crop':
                    # 恢复任意形状选区
                    points = [QPoint(x, y) for x, y in shape_data.get('points', [])]
                    original_points = [QPoint(x, y) for x, y in shape_data.get('original_points', [])]
                    offset_x, offset_y = shape_data.get('offset', (0, 0))
                    
                    if len(points) >= 3:
                        self.crop_points = points
                        self.crop_selection_original_points = original_points if original_points else points
                        self.crop_selection_content = pixmap
                        self.crop_selection_offset = QPoint(offset_x, offset_y)
                        
                        # 计算边界矩形
                        min_x = min(p.x() for p in points)
                        max_x = max(p.x() for p in points)
                        min_y = min(p.y() for p in points)
                        max_y = max(p.y() for p in points)
                        self.crop_selection_rect = QRect(min_x, min_y, max_x - min_x, max_y - min_y)
                        
                        self.crop_selection_active = True
                        self.crop_selection_dragging = False
                        
                        # 将粘贴位置调整到画布中央
                        center_x = self.image.width() // 2
                        center_y = self.image.height() // 2
                        rect_center_x = self.crop_selection_rect.center().x()
                        rect_center_y = self.crop_selection_rect.center().y()
                        self.crop_selection_offset = QPoint(
                            center_x - rect_center_x,
                            center_y - rect_center_y
                        )
                        
                else:  # rect
                    # 恢复矩形选区
                    if 'rect' in shape_data:
                        x, y, w, h = shape_data['rect']
                        self.selection_rect = QRect(x, y, w, h)
                    else:
                        # 创建新的矩形选区，位置在画布中央
                        center_x = self.image.width() // 2
                        center_y = self.image.height() // 2
                        x = center_x - pixmap.width() // 2
                        y = center_y - pixmap.height() // 2
                        self.selection_rect = QRect(x, y, pixmap.width(), pixmap.height())
                    
                    self.selection_content = pixmap
                    self.selection_active = True
                    self.selection_transform_mode = "move"
                    
            except (json.JSONDecodeError, KeyError, ValueError):
                # 如果解析失败，回退到普通粘贴
                has_custom_shape = False
                
        if not has_custom_shape:
            # 普通粘贴（兼容旧版本）
            pixmap = clipboard.pixmap()
            if pixmap.isNull():
                return False
                
            # 如果有当前矩形选区，先提交
            if self.selection_active:
                self.commit_selection()
            
            # 如果有当前任意形状选区，先提交
            if self.crop_selection_active:
                self.commit_crop_selection()
            
            # 创建新的矩形选区，位置在画布中央
            center_x = self.image.width() // 2
            center_y = self.image.height() // 2
            x = center_x - pixmap.width() // 2
            y = center_y - pixmap.height() // 2
            
            self.selection_content = pixmap
            self.selection_rect = QRect(x, y, pixmap.width(), pixmap.height())
            self.selection_active = True
            self.selection_transform_mode = "move"
            
        self.update()
        return True
        
    def paintEvent(self, event):
        painter = QPainter(self)

        # 缩放变换：所有绘制都在缩放坐标系下进行
        if self.zoom_factor != 1.0:
            painter.scale(self.zoom_factor, self.zoom_factor)

        # 绘制图像（按原尺寸，不拉伸）
        painter.drawPixmap(0, 0, self.image)
        
        # 绘制矩形选区内容（如果有）
        if self.selection_active and self.selection_content is not None:
            painter.drawPixmap(self.selection_rect.topLeft(), self.selection_content)
        
        # 如果是文字模式且正在输入，绘制文本框
        if self.is_text_mode and self.text_start_point and self.text_content:
            painter.setPen(QPen(Qt.black, 1, Qt.DashLine))
            font_metrics = painter.fontMetrics()
            text_width = font_metrics.width(self.text_content)
            text_height = font_metrics.height()
            text_rect = QRect(self.text_start_point, QSize(text_width + 10, text_height + 5))
            painter.drawRect(text_rect)
        
        # 绘制选区矩形（虚线）
        if self.selection_active and not self.selection_rect.isEmpty():
            painter.setPen(QPen(Qt.blue, 1, Qt.DashLine))
            painter.drawRect(self.selection_rect)
        
        # 绘制任意形状选区（正在绘制中）
        if self.crop_drawing and len(self.crop_points) > 1:
            painter.setPen(QPen(Qt.blue, 1, Qt.DashLine))
            for i in range(len(self.crop_points) - 1):
                painter.drawLine(self.crop_points[i], self.crop_points[i + 1])
            # 如果正在绘制，连接最后一个点与当前鼠标位置
            if self.drawing and self.current_tool == "crop" and len(self.crop_points) > 1:
                painter.drawLine(self.crop_points[-1], self.last_point)
        
        # 绘制激活的任意形状选区内容和边框
        if self.crop_selection_active and self.crop_selection_content is not None:
            # 计算当前选区位置
            current_rect = self.crop_selection_rect.translated(self.crop_selection_offset)
            
            # 绘制选区内容
            painter.drawPixmap(current_rect.topLeft(), self.crop_selection_content)
            
            # 绘制选区边框（虚线多边形）
            painter.setPen(QPen(Qt.blue, 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            
            # 绘制多边形边框
            if len(self.crop_selection_original_points) >= 3:
                offset = current_rect.topLeft()
                for i in range(len(self.crop_selection_original_points)):
                    p1 = self.crop_selection_original_points[i] + offset
                    p2 = self.crop_selection_original_points[(i + 1) % len(self.crop_selection_original_points)] + offset
                    painter.drawLine(p1, p2)
        
        # 绘制多边形预览（对标微软画图）
        if self.polygon_drawing and len(self.polygon_points) > 0:
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 根据最后使用的鼠标按钮确定颜色
            draw_color = self.pen_color if getattr(self, 'last_button', Qt.LeftButton) == Qt.LeftButton else self.bg_color
            
            # 绘制已确定的边（实线）
            painter.setPen(QPen(draw_color, self.pen_width, self.pen_style, Qt.RoundCap, Qt.RoundJoin))
            for i in range(len(self.polygon_points) - 1):
                painter.drawLine(self.polygon_points[i], self.polygon_points[i + 1])
            
            # 绘制预览线（虚线，到鼠标位置）
            if hasattr(self, '_last_mouse_pos') and self._last_mouse_pos:
                painter.setPen(QPen(draw_color, 1, Qt.DashLine))
                # 从最后一个点到鼠标的预览线
                painter.drawLine(self.polygon_points[-1], self._last_mouse_pos)
                # 闭合预览线（从鼠标到起始点）
                if len(self.polygon_points) >= 2:
                    painter.drawLine(self._last_mouse_pos, self.polygon_points[0])
            
            # 绘制顶点标记
            for i, point in enumerate(self.polygon_points):
                if i == 0:
                    # 起始点用方块标记
                    painter.setPen(QPen(draw_color, 1, Qt.SolidLine))
                    painter.setBrush(QBrush(draw_color))
                    painter.drawRect(point.x() - 3, point.y() - 3, 6, 6)
                else:
                    # 其他点用圆点标记
                    painter.setPen(QPen(draw_color, 1, Qt.SolidLine))
                    painter.setBrush(QBrush(draw_color))
                    painter.drawEllipse(point, 3, 3)
        
        # 绘制曲线预览（Catmull-Rom样条）
        if self.curve_drawing and len(self.curve_points) > 0:
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 根据鼠标按钮确定颜色
            draw_color = self.pen_color if self.curve_button == Qt.LeftButton else self.bg_color
            
            # 绘制已确定的曲线
            if len(self.curve_points) >= 2:
                # 绘制实际的曲线
                temp_points = list(self.curve_points)
                self.draw_catmull_rom_curve(temp_points, painter)
            
            # 绘制预览曲线（包含鼠标位置）
            if hasattr(self, '_last_mouse_pos') and self._last_mouse_pos and len(self.curve_points) >= 1:
                painter.setPen(QPen(draw_color, 1, Qt.DashLine))
                # 添加鼠标位置作为临时控制点绘制预览
                preview_points = list(self.curve_points) + [self._last_mouse_pos]
                if len(preview_points) >= 2:
                    # 绘制到鼠标位置的预览线
                    temp_color = QColor(draw_color)
                    temp_color.setAlpha(128)  # 半透明
                    painter.setPen(QPen(temp_color, 1, Qt.DashLine))
                    
                    if len(preview_points) == 2:
                        painter.drawLine(preview_points[0], preview_points[1])
                    elif len(preview_points) == 3:
                        curve_points = self.catmull_rom_spline(preview_points[0], preview_points[0], 
                                                               preview_points[1], preview_points[2], 10)
                        for i in range(len(curve_points) - 1):
                            painter.drawLine(curve_points[i], curve_points[i + 1])
                        curve_points = self.catmull_rom_spline(preview_points[0], preview_points[1], 
                                                               preview_points[2], preview_points[2], 10)
                        for i in range(len(curve_points) - 1):
                            painter.drawLine(curve_points[i], curve_points[i + 1])
                    else:
                        # 绘制最后一段预览
                        curve_points = self.catmull_rom_spline(preview_points[-4], preview_points[-3], 
                                                               preview_points[-2], preview_points[-1], 10)
                        for i in range(len(curve_points) - 1):
                            painter.drawLine(curve_points[i], curve_points[i + 1])
            
            # 绘制控制点标记
            painter.setPen(QPen(draw_color, 1, Qt.SolidLine))
            painter.setBrush(QBrush(draw_color))
            for i, point in enumerate(self.curve_points):
                if i == 0:
                    # 起始点用方块标记
                    painter.drawRect(point.x() - 3, point.y() - 3, 6, 6)
                else:
                    # 其他点用圆点标记
                    painter.drawEllipse(point, 3, 3)

        # 绘制调整大小控制点
        if not self.drawing and not self.selection_active and not self.crop_drawing:
            # 只在没有其他交互时显示控制点
            painter.setPen(QPen(Qt.blue, 1, Qt.SolidLine))
            painter.setBrush(QBrush(QColor(200, 200, 255, 200)))
            handle_size = self.resize_handle_size
            
            # 画布尺寸
            canvas_width = self.image.width()
            canvas_height = self.image.height()
            
            # 右侧边缘控制点（在右侧边缘中间）
            right_x = canvas_width - handle_size
            right_y = canvas_height // 2 - handle_size // 2
            painter.drawRect(right_x, right_y, handle_size, handle_size)
            
            # 下侧边缘控制点（在下侧边缘中间）
            bottom_x = canvas_width // 2 - handle_size // 2
            bottom_y = canvas_height - handle_size
            painter.drawRect(bottom_x, bottom_y, handle_size, handle_size)
            
            # 右下角控制点
            corner_x = canvas_width - handle_size
            corner_y = canvas_height - handle_size
            painter.drawRect(corner_x, corner_y, handle_size, handle_size)
    
    def mousePressEvent(self, event):
        # ── 放大镜工具：左键放大，右键缩小，不进入绘图流程 ──
        if self.current_tool == "magnifier":
            if event.button() == Qt.LeftButton:
                self.zoom_in()
            elif event.button() == Qt.RightButton:
                self.zoom_out()
            return

        # ── 坐标转换：widget 坐标 → 图像坐标（缩放时使用）──
        # 用一个代理事件位置，后续所有 event.pos() 都走此转换
        _img_pos = self._widget_to_image(event.pos())
        # 覆盖 event.pos，使后续所有代码透明地拿到图像坐标
        event.pos = lambda: _img_pos

        # 如果正在文字模式，检查是否点击在输入框外，如果是则提交文字
        if self.is_text_mode and self.text_input_widget:
            # 获取输入框的全局位置
            widget_rect = QRect(self.text_input_widget.pos(), self.text_input_widget.size())
            if not widget_rect.contains(_img_pos):
                # 点击在输入框外，提交文字
                self.finish_text_input()
                # 如果是文字工具，继续处理（创建新的输入框）
                # 如果不是文字工具，已经提交，直接返回
                if self.current_tool != "text":
                    return
        
        if event.button() in [Qt.LeftButton, Qt.RightButton]:
            # 检查是否点击了调整大小控制点
            if not self.drawing and not self.selection_active and not self.crop_drawing:
                handle_size = self.resize_handle_size
                canvas_width = self.image.width()
                canvas_height = self.image.height()
                
                # 右侧边缘控制点矩形（在右侧边缘中间）
                right_rect = QRect(canvas_width - handle_size,
                                   canvas_height // 2 - handle_size // 2,
                                   handle_size, handle_size)
                # 下侧边缘控制点矩形（在下侧边缘中间）
                bottom_rect = QRect(canvas_width // 2 - handle_size // 2,
                                    canvas_height - handle_size,
                                    handle_size, handle_size)
                # 右下角控制点矩形
                corner_rect = QRect(canvas_width - handle_size,
                                    canvas_height - handle_size,
                                    handle_size, handle_size)
                
                pos = event.pos()
                if right_rect.contains(pos):
                    self.save_state()  # 操作前保存状态
                    self.resizing_mode = "right"
                    self.resizing_start_pos = pos
                    self.original_size = self.image.size()
                    self.original_image = self.image.copy()
                    return
                elif bottom_rect.contains(pos):
                    self.save_state()  # 操作前保存状态
                    self.resizing_mode = "bottom"
                    self.resizing_start_pos = pos
                    self.original_size = self.image.size()
                    self.original_image = self.image.copy()
                    return
                elif corner_rect.contains(pos):
                    self.save_state()  # 操作前保存状态
                    self.resizing_mode = "corner"
                    self.resizing_start_pos = pos
                    self.original_size = self.image.size()
                    self.original_image = self.image.copy()
                    return
            
            # 优先检查是否点击在异型选区内（任何工具下都可以拖动异型选区）
            if self.crop_selection_active and self.is_point_in_crop_selection(event.pos()):
                # 在异型选区内点击，开始移动选区
                self.crop_selection_dragging = True
                self.selection_start_pos = event.pos()
                self.drawing = False  # 不是绘制模式
                self.update()
                return  # 直接返回，不继续处理其他逻辑
            
            # 检查是否点击在矩形选区内（任何工具下都可以拖动矩形选区）
            if self.selection_active and self.selection_rect.contains(event.pos()):
                # 在矩形选区内点击，开始移动选区
                self.selection_transform_mode = "move"
                self.selection_start_pos = event.pos()
                self.drawing = False  # 不是绘制模式
                self.update()
                return  # 直接返回，不继续处理其他逻辑
            
            # 多边形工具的特殊处理（在选区检测之后处理）
            if self.current_tool == "polygon":
                # 左键和右键都可以绘制多边形
                if event.button() in [Qt.LeftButton, Qt.RightButton]:
                    # 检测双击（300ms内的第二次点击相同按钮）
                    import time
                    current_time = time.time() * 1000  # 转换为毫秒
                    time_diff = current_time - self._last_polygon_click_time
                    
                    # 检查是否双击同一个按钮
                    same_button = (getattr(self, 'last_button', None) == event.button())
                    
                    if self.polygon_drawing and time_diff < 300 and same_button and len(self.polygon_points) >= 3:
                        # 双击相同按钮完成多边形
                        self.finish_polygon()
                        return
                    
                    # 单击添加顶点
                    if not self.polygon_drawing:
                        # 第一次点击，开始绘制
                        self.polygon_drawing = True
                        self.polygon_points = [event.pos()]
                        self.temp_image = self.image.copy()  # 保存预览图像
                        self.last_button = event.button()  # 记录按钮（左键=前景色，右键=背景色）
                    else:
                        # 检查是否切换了按钮（从左键切换到右键或相反）
                        if self.last_button != event.button():
                            # 切换了按钮，取消当前多边形绘制
                            self.cancel_polygon()
                            # 开始新的多边形绘制
                            self.polygon_drawing = True
                            self.polygon_points = [event.pos()]
                            self.temp_image = self.image.copy()
                            self.last_button = event.button()
                        else:
                            # 同一个按钮，添加顶点到现有多边形
                            self.polygon_points.append(event.pos())
                    
                    self._last_polygon_click_time = current_time
                    self.update()
                    return
            
            # 曲线工具的特殊处理（在选区检测之后处理）
            if self.current_tool == "curve":
                # 左键和右键都可以绘制曲线
                if event.button() in [Qt.LeftButton, Qt.RightButton]:
                    # 检测双击（300ms内的第二次点击相同按钮）
                    import time
                    current_time = time.time() * 1000  # 转换为毫秒
                    time_diff = current_time - self._last_curve_click_time
                    
                    # 检查是否双击同一个按钮
                    same_button = (self.curve_button == event.button())
                    
                    if self.curve_drawing and time_diff < 300 and same_button and len(self.curve_points) >= 2:
                        # 双击相同按钮完成曲线
                        self.finish_curve()
                        return
                    
                    # 单击添加控制点
                    if not self.curve_drawing:
                        # 第一次点击，开始绘制
                        self.curve_drawing = True
                        self.curve_points = [event.pos()]
                        self.temp_image = self.image.copy()  # 保存预览图像
                        self.curve_button = event.button()  # 记录按钮（左键=前景色，右键=背景色）
                    else:
                        # 检查是否切换了按钮（从左键切换到右键或相反）
                        if self.curve_button != event.button():
                            # 切换了按钮，取消当前曲线绘制
                            self.cancel_curve()
                            # 开始新的曲线绘制
                            self.curve_drawing = True
                            self.curve_points = [event.pos()]
                            self.temp_image = self.image.copy()
                            self.curve_button = event.button()
                        else:
                            # 同一个按钮，添加控制点到现有曲线
                            self.curve_points.append(event.pos())
                    
                    self._last_curve_click_time = current_time
                    self.update()
                    return
            
            # 如果没有点击控制点和选区，则进行正常的绘图操作
            
            # 如果在文字模式下点击画布，检查是否点击在文字输入框外
            if self.is_text_mode and self.text_input_widget:
                # 检查点击位置是否在文字输入框内
                input_widget_rect = self.text_input_widget.geometry()
                if not input_widget_rect.contains(event.pos()):
                    # 点击在输入框外，提交文字
                    self.finish_text_input()
                    # 如果当前工具不是文字工具，继续处理当前工具的绘制
                    if self.current_tool != "text":
                        pass  # 继续往下执行
                    else:
                        # 如果还是文字工具，则不继续（避免立即创建新输入框）
                        return
            
            # 在操作前保存状态（排除纯预览/选区/取色器等不修改像素的工具）
            if self.current_tool not in ["eyedropper", "select", "crop"]:
                self.save_state()

            self.drawing = True
            self.last_point = event.pos()
            self.start_point = event.pos()
            self.last_button = event.button()  # 记录最后使用的鼠标按钮
            
            # 保存临时图像用于预览
            if self.current_tool in ["line", "rectangle", "ellipse", "rounded"]:
                self.temp_image = self.image.copy()
            
            # 根据鼠标按钮确定绘图颜色
            draw_color = self.pen_color if event.button() == Qt.LeftButton else self.bg_color
            
            # 填充工具
            if self.current_tool == "fill":
                # 保存当前颜色并设置填充颜色
                original_color = self.pen_color
                self.pen_color = draw_color
                self.flood_fill(event.pos())
                self.pen_color = original_color  # 恢复原始颜色
                self.mark_content_modified()
            
            # 取色器工具
            if self.current_tool == "eyedropper":
                self.pick_color(event.pos())
            
            # 喷枪工具
            if self.current_tool == "airbrush":
                self.current_spray_pos = event.pos()
                # 保存当前颜色并设置喷枪颜色
                original_color = self.pen_color
                self.pen_color = draw_color
                self.spray_paint()
                self.pen_color = original_color  # 恢复原始颜色
                self.airbrush_timer.start(50)  # 每50毫秒喷一次
            
            # 文字工具
            if self.current_tool == "text":
                # 如果已经处于文字模式，先完成当前输入
                if self.is_text_mode and self.text_input_widget:
                    self.finish_text_input()
                
                # 开始新的文字输入
                self.is_text_mode = True
                self.text_start_point = event.pos()
                self.text_content = ""
                # 根据鼠标按钮设置文字颜色
                self.pen_color = draw_color
                
                # 显示文字工具栏（如果还没创建）
                if not self.text_tool_dialog:
                    self.text_tool_dialog = TextToolDialog()
                    # 连接字体变化信号到文字输入框更新
                    self.text_tool_dialog.font_changed.connect(self.update_text_input_font)
                    # 连接对话框关闭信号，更新菜单状态
                    if hasattr(self, 'parent') and hasattr(self.parent(), 'on_text_toolbar_closed'):
                        self.text_tool_dialog.finished.connect(self.parent().on_text_toolbar_closed)
                    # 连接对话框销毁信号，确保清理引用
                    self.text_tool_dialog.destroyed.connect(self.on_text_toolbar_destroyed)
                
                # 显示工具栏
                self.text_tool_dialog.show()
                # 确保菜单项为选中状态（带钩）
                if hasattr(self, 'parent') and hasattr(self.parent(), 'text_toolbar_action'):
                    self.parent().text_toolbar_action.setChecked(True)
                
                # 创建文字输入框
                if self.text_input_widget:
                    self.text_input_widget.hide()
                    self.text_input_widget.deleteLater()
                    self.text_input_widget = None
                
                # 创建新的文字输入框
                self.text_input_widget = TextInputWidget(self, event.pos())
                self.text_input_widget.move(event.pos())
                
                # 应用当前字体到文字输入框
                if self.text_tool_dialog:
                    current_font = self.text_tool_dialog.get_font()
                    self.text_input_widget.setFont(current_font)
                    self.text_font = current_font  # 同步更新存储的字体
                else:
                    self.text_input_widget.setFont(self.text_font)
                
                # 移除双向绑定，避免循环信号问题
                # 只保留工具栏到输入框的单向同步
                # 这样可以避免：setFont -> selection_font_changed -> set_font_from_widget -> on_font_changed 的循环
                    # 立即同步一次，确保工具栏显示正确的状态
                    QTimer.singleShot(0, lambda: self.text_tool_dialog.set_font_from_widget(
                        self.text_input_widget.font()) if self.text_input_widget else None)
                
                self.text_input_widget.show()
                
                # 设置焦点到文字输入框 - 使用稍长的延迟确保正确设置
                QTimer.singleShot(50, self.text_input_widget.setFocus)
                
                # 设置文字颜色为当前前景色
                self.update_text_input_color(self.pen_color)
                
                # 连接输入框的完成信号
                self.text_input_widget.returnPressed.connect(self.finish_text_input)
                
                self.update()
            
            # 矩形选取工具（只有在当前工具是select时才建立新选区）
            if self.current_tool == "select":
                # 建立新选区或调整选区
                if self.selection_active:
                    # 已有选区，先提交当前选区内容
                    self.commit_selection()
                
                self.selection_active = True
                self.selection_rect.setTopLeft(event.pos())
                self.selection_rect.setBottomRight(event.pos())
                self.selection_dragging = True
                self.selection_transform_mode = "resize"
                self.update()
            
            # 处理在选区外点击的情况 - 提交当前选区
            if self.selection_active and not self.selection_rect.contains(event.pos()):
                if self.current_tool != "select":
                    # 非选择工具下，在选区外点击，提交选区
                    self.commit_selection()
            
            # 处理任意形状选区外点击的情况
            if self.crop_selection_active and not self.is_point_in_crop_selection(event.pos()):
                if self.current_tool != "crop":
                    # 非裁剪工具下，在选区外点击，提交选区
                    self.commit_crop_selection()
            
            # 任意形状选择工具
            if self.current_tool == "crop":
                # 注意：如果已经在上面处理了crop_selection拖动，就不会到这里
                # 因为上面有return语句
                
                # 如果没有激活的选区，或者点击在选区外
                if not self.crop_selection_active:
                    # 开始新的多边形选区绘制
                    self.crop_drawing = True
                    self.crop_points = [event.pos()]
                    self.drawing = True  # 设置绘制状态
                elif not self.is_point_in_crop_selection(event.pos()):
                    # 如果已有选区但点击在选区外，先提交再开始新选区
                    self.commit_crop_selection()
                    self.crop_drawing = True
                    self.crop_points = [event.pos()]
                    self.drawing = True
                self.update()
    
    def mouseMoveEvent(self, event):
        # 坐标转换：widget 坐标 → 图像坐标
        _img_pos = self._widget_to_image(event.pos())
        event.pos = lambda: _img_pos

        # 放大镜工具：鼠标移动时不做绘图处理
        if self.current_tool == "magnifier":
            return

        # 处理画布调整大小 - 支持左右键
        if self.resizing_mode is not None and (event.buttons() & (Qt.LeftButton | Qt.RightButton)):
            if self.original_image is None:
                return
            delta_x = event.pos().x() - self.resizing_start_pos.x()
            delta_y = event.pos().y() - self.resizing_start_pos.y()
            
            new_width = max(self.original_size.width(), 1)
            new_height = max(self.original_size.height(), 1)
            
            if self.resizing_mode == "right":
                new_width = max(self.original_size.width() + delta_x, 1)
                new_height = self.original_size.height()
            elif self.resizing_mode == "bottom":
                new_width = self.original_size.width()
                new_height = max(self.original_size.height() + delta_y, 1)
            elif self.resizing_mode == "corner":
                new_width = max(self.original_size.width() + delta_x, 1)
                new_height = max(self.original_size.height() + delta_y, 1)
            
            # 创建新图像
            new_image = QPixmap(new_width, new_height)
            new_image.fill(self.bg_color)
            
            # 将原始图像绘制到新画布上
            painter = QPainter(new_image)
            painter.drawPixmap(0, 0, self.original_image)
            painter.end()
            
            self.image = new_image
            # 调整画布组件尺寸以匹配新图像大小（保持当前缩放）
            self._apply_zoom()
            self.mark_content_modified()
            return
        
        # 处理任意形状选区拖动（独立于 self.drawing 状态，任何工具下都可以拖动）
        if self.crop_selection_dragging and (event.buttons() & (Qt.LeftButton | Qt.RightButton)):
            # 拖动已激活的选区
            delta = event.pos() - self.selection_start_pos
            self.crop_selection_offset += delta
            self.selection_start_pos = event.pos()
            self.update()
            return
        
        # 处理矩形选区移动（独立于绘图状态，任何工具下都可以拖动）
        if self.selection_active and self.selection_transform_mode == "move" and (event.buttons() & (Qt.LeftButton | Qt.RightButton)):
            # 移动矩形选区
            delta = event.pos() - self.selection_start_pos
            self.selection_rect.translate(delta)
            self.selection_start_pos = event.pos()
            self.update()
            return
        
        # 原有的绘图逻辑 - 支持左右键
        if self.drawing and (event.buttons() & (Qt.LeftButton | Qt.RightButton)):
            
            if self.current_tool == "pencil":
                # 铅笔工具 - 自由绘制
                painter = QPainter(self.image)
                # 根据最后使用的鼠标按钮确定颜色
                draw_color = self.pen_color if getattr(self, 'last_button', Qt.LeftButton) == Qt.LeftButton else self.bg_color
                painter.setPen(QPen(draw_color, self.pen_width,
                                   self.pen_style, Qt.RoundCap, Qt.RoundJoin))
                painter.drawLine(self.last_point, event.pos())
                painter.end()
                self.last_point = event.pos()
                self.update()
                self.mark_content_modified()
                
            elif self.current_tool == "brush":
                # 刷子工具 - 粗笔刷
                painter = QPainter(self.image)
                # 根据最后使用的鼠标按钮确定颜色
                draw_color = self.pen_color if getattr(self, 'last_button', Qt.LeftButton) == Qt.LeftButton else self.bg_color
                painter.setPen(QPen(draw_color, self.pen_width * 3,
                                   self.pen_style, Qt.RoundCap, Qt.RoundJoin))
                painter.drawLine(self.last_point, event.pos())
                painter.end()
                self.last_point = event.pos()
                self.update()
                self.mark_content_modified()
                
            elif self.current_tool == "eraser":
                # 橡皮擦工具 - 改进功能
                # 获取当前位置的颜色
                image = self.image.toImage()
                
                # 根据最后使用的鼠标按钮确定擦除模式
                if getattr(self, 'last_button', Qt.LeftButton) == Qt.LeftButton:
                    # 左键：保持原来的线条擦除效果，但只擦除非背景色
                    painter = QPainter(self.image)
                    painter.setPen(QPen(self.bg_color, self.pen_width * 4,
                                       self.pen_style, Qt.RoundCap, Qt.RoundJoin))
                    
                    # 使用较小的步长进行采样，实现更精确的擦除
                    step = max(1, self.pen_width // 2)  # 根据笔宽调整采样密度
                    dx = event.pos().x() - self.last_point.x()
                    dy = event.pos().y() - self.last_point.y()
                    distance = (dx*dx + dy*dy) ** 0.5
                    
                    if distance > 0:
                        steps = max(1, int(distance / step))
                        for i in range(steps + 1):
                            t = i / steps
                            x = int(self.last_point.x() + t * dx)
                            y = int(self.last_point.y() + t * dy)
                            
                            if 0 <= x < self.image.width() and 0 <= y < self.image.height():
                                current_color = image.pixelColor(x, y)
                                # 如果当前颜色不是背景色，则擦除
                                if current_color != self.bg_color:
                                    painter.drawPoint(x, y)
                    
                    painter.end()
                else:
                    # 右键：像素级精确替换前景色
                    # 计算擦除区域（圆形区域）
                    radius = self.pen_width * 2
                    center_x = event.pos().x()
                    center_y = event.pos().y()
                    
                    for dx in range(-radius, radius + 1):
                        for dy in range(-radius, radius + 1):
                            if dx*dx + dy*dy <= radius*radius:  # 圆形区域
                                x = center_x + dx
                                y = center_y + dy
                                if 0 <= x < self.image.width() and 0 <= y < self.image.height():
                                    current_color = image.pixelColor(x, y)
                                    # 如果当前颜色是前景色，则用背景色替换
                                    if current_color == self.pen_color:
                                        image.setPixelColor(x, y, self.bg_color)
                    
                    # 将修改后的图像设置回去
                    self.image = QPixmap.fromImage(image)
                
                self.last_point = event.pos()
                self.update()
                self.mark_content_modified()
            
            elif self.current_tool == "airbrush":
                # 喷枪工具 - 更新喷射位置并使用相应颜色
                self.current_spray_pos = event.pos()
                # 根据最后使用的鼠标按钮确定颜色
                draw_color = self.pen_color if getattr(self, 'last_button', Qt.LeftButton) == Qt.LeftButton else self.bg_color
                # 保存当前颜色并设置喷枪颜色
                original_color = self.pen_color
                self.pen_color = draw_color
                self.spray_paint()
                self.pen_color = original_color  # 恢复原始颜色
                
            elif self.current_tool == "select":
                # 矩形选取工具处理 - 支持左右键
                if self.selection_transform_mode == "resize" and (event.buttons() & (Qt.LeftButton | Qt.RightButton)):
                    # 调整选区大小
                    self.selection_rect.setBottomRight(event.pos())
                # 移动模式已经在前面统一处理
                self.update()
                
            elif self.current_tool == "crop":
                # 任意形状选择工具处理
                # 注意：crop_selection_dragging的拖动已经在前面统一处理了
                if self.crop_drawing and (event.buttons() & (Qt.LeftButton | Qt.RightButton)):
                    # 继续绘制多边形选区，添加新的点
                    if len(self.crop_points) > 0:
                        # 只有当点距离上一个点足够远时才添加新点
                        last_point = self.crop_points[-1]
                        if (abs(event.pos().x() - last_point.x()) > 3 or 
                            abs(event.pos().y() - last_point.y()) > 3):
                            self.crop_points.append(event.pos())
                self.update()
            
            elif self.current_tool == "polygon":
                # 多边形绘制工具 - 记录鼠标位置并触发重绘
                self._last_mouse_pos = event.pos()
                self.update()
            
            elif self.current_tool == "curve":
                # 曲线绘制工具 - 记录鼠标位置并触发重绘
                self._last_mouse_pos = event.pos()
                self.update()
                
            elif self.current_tool in ["line", "rectangle", "ellipse", "rounded"]:
                # 形状工具 - 显示预览
                self.image = self.temp_image.copy()
                painter = QPainter(self.image)
                # 根据最后使用的鼠标按钮确定颜色
                draw_color = self.pen_color if getattr(self, 'last_button', Qt.LeftButton) == Qt.LeftButton else self.bg_color
                painter.setPen(QPen(draw_color, self.pen_width,
                                   self.pen_style, Qt.RoundCap, Qt.RoundJoin))
                self.draw_shape(painter, self.start_point, event.pos())
                painter.end()
                self.update()
            
    def mouseReleaseEvent(self, event):
        # 坐标转换：widget 坐标 → 图像坐标
        _img_pos = self._widget_to_image(event.pos())
        event.pos = lambda: _img_pos

        if event.button() == Qt.LeftButton:
            # 结束画布调整大小
            if self.resizing_mode is not None:
                self.resizing_mode = None
                self.original_image = None
                return
            if self.drawing and self.current_tool in ["line", "rectangle", "ellipse", "rounded"]:
                # 完成形状绘制
                painter = QPainter(self.image)
                # 根据最后使用的鼠标按钮确定颜色
                draw_color = self.pen_color if getattr(self, 'last_button', Qt.LeftButton) == Qt.LeftButton else self.bg_color
                painter.setPen(QPen(draw_color, self.pen_width,
                                   self.pen_style, Qt.RoundCap, Qt.RoundJoin))
                self.draw_shape(painter, self.start_point, event.pos())
                self.update()
                self.mark_content_modified()
            
            # 停止喷枪
            if self.current_tool == "airbrush":
                self.airbrush_timer.stop()
            
            # 文字工具完成输入
            if self.current_tool == "text" and self.is_text_mode and self.text_content:
                painter = QPainter(self.image)
                # 文字颜色已经在mousePressEvent中设置
                painter.setPen(QPen(self.pen_color, 1))
                painter.setFont(self.text_font)
                painter.drawText(self.text_start_point, self.text_content)
                painter.end()
                self.update()
                self.mark_content_modified()
            
            # 完成矩形选取
            if self.current_tool == "select":
                self.selection_dragging = False
                if self.selection_transform_mode == "resize":
                    # 调整大小模式，捕获选区内容
                    self.capture_selection_content()
                elif self.selection_transform_mode == "move":
                    # 移动模式，不需要额外处理，位置已经更新
                    pass
                self.selection_transform_mode = None
                self.update()
            
            # 完成矩形选区移动（任何工具下都可以结束移动）
            if self.selection_active and self.selection_transform_mode == "move":
                self.selection_transform_mode = None
                self.update()
            
            # 完成任意形状选择（任何工具下都可以结束拖动）
            if self.crop_selection_dragging:
                # 结束拖动选区
                self.crop_selection_dragging = False
                self.update()
            elif self.current_tool == "crop":
                # 只有在crop工具下才处理绘制完成
                if self.crop_drawing:
                    # 完成多边形选区绘制
                    self.crop_drawing = False
                    if len(self.crop_points) >= 3:
                        # 捕获选区内容（而非执行裁剪）
                        self.capture_crop_selection_content()
                    else:
                        # 点太少，清除绘制
                        self.crop_points = []
                self.update()
            
            # 完成多边形绘制
            if self.current_tool == "polygon":
                # 多边形绘制在鼠标按下时已经完成，这里不需要额外处理
                pass
                
            self.drawing = False
            self.temp_image = None
            # 文字模式不在此结束，而是在finish_text_input中处理
    
    def finish_text_input(self):
        """完成文字输入 - 简化版"""
        if not self.text_input_widget:
            return
            
        text = self.text_input_widget.text().strip()
        if text:
            # 获取当前字体
            if self.text_tool_dialog:
                current_font = self.text_tool_dialog.get_font()
            else:
                current_font = self.text_font
            
            self.save_state()  # 操作前保存状态
            
            # 绘制文字到画布 - 修复位置对齐问题
            painter = QPainter(self.image)
            painter.setPen(QPen(self.pen_color, 1))
            painter.setFont(current_font)
            
            # 获取字体度量信息，用于精确位置计算
            font_metrics = painter.fontMetrics()
            
            # 计算正确的绘制位置
            # QLineEdit的文字显示位置 vs drawText的基线位置需要精确对齐
            # 方法：使用更精确的计算方式来匹配QLineEdit的文本显示位置
            
            # QLineEdit的布局分析：
            # 1. 边框: 2px (根据样式表设置)
            # 2. 内边距: 4px (根据样式表设置)
            # 3. 文本垂直居中显示
            
            border_width = 2  # 边框宽度
            padding = 4       # 内边距
            
            # 获取字体度量信息
            ascent = font_metrics.ascent()
            
            # 使用最简单的匹配方法：直接使用ascent值作为Y偏移
            # 这是最接近QLineEdit中文本显示位置的方法
            draw_pos = QPoint(
                self.text_start_point.x() + border_width + padding,
                self.text_start_point.y() + border_width + padding + ascent
            )
            
            # 使用更精确的文本绘制
            painter.drawText(draw_pos, text)
            painter.end()
            self.update()
            self.mark_content_modified()
        
        # 清理输入框
        if self.text_input_widget:
            self.text_input_widget.hide()
            self.text_input_widget.deleteLater()
            self.text_input_widget = None
        self.is_text_mode = False
        self.text_content = ""
    
    def on_text_toolbar_destroyed(self):
        """文字工具栏销毁时的处理"""
        # 清理对话框引用
        self.text_tool_dialog = None
        # 更新菜单状态为未选中
        if hasattr(self, 'parent') and hasattr(self.parent(), 'text_toolbar_action'):
            self.parent().text_toolbar_action.setChecked(False)
    
    def update_text_input_color(self, color):
        """更新文字输入框的文字颜色"""
        if self.text_input_widget:
            # 创建样式表，设置文字颜色
            style = f"""
                QLineEdit {{
                    border: 2px solid #316AC5;
                    border-radius: 3px;
                    background-color: transparent;
                    padding: 4px;
                    color: {color.name()};  /* 设置文字颜色为前景色 */
                    selection-background-color: #316AC5;
                    selection-color: white;
                }}
                QLineEdit:focus {{
                    border-color: #316AC5;
                    outline: none;
                }}
            """
            self.text_input_widget.setStyleSheet(style)
    
    def on_text_input_moved(self, new_pos):
        """文字输入框位置变化时的处理"""
        # 更新文字起始位置，确保提交时在正确的位置
        self.text_start_point = new_pos
        print(f"文字输入框移动到: {new_pos}")
        
    def update_text_input_font(self, font):
        """更新文字输入框的字体 - 增强焦点和文字管理"""
        self.text_font = font
        if self.text_input_widget:
            # 保存当前状态
            current_text = self.text_input_widget.text()
            cursor_pos = self.text_input_widget.cursorPosition()
            current_pos = self.text_input_widget.pos()
            has_focus = self.text_input_widget.hasFocus()
            
            # 应用新字体 - 这会触发setFont方法自动调整大小
            self.text_input_widget.setFont(font)
            
            # 确保文字内容保持不变（重要：这也会更新文字大小）
            if current_text:
                self.text_input_widget.setText(current_text)
                self.text_input_widget.setCursorPosition(min(cursor_pos, len(current_text)))
            
            # 确保位置正确
            self.text_input_widget.move(current_pos)
            
            # 强制保持焦点 - 使用延迟确保焦点不被抢夺
            if has_focus:
                QTimer.singleShot(0, lambda: self.text_input_widget and self.text_input_widget.setFocus())
            
            # 强制立即更新显示
            self.text_input_widget.update()
            self.text_input_widget.repaint()
            
            # 确保父画布也更新
            self.update()
    
    def spray_paint(self):
        """喷枪效果 - 在当前位置随机喷洒颜色点"""
        if not self.drawing:
            return
        
        painter = QPainter(self.image)
        painter.setPen(QPen(self.pen_color, 1, Qt.SolidLine))
        
        # 喷洒半径
        spray_radius = self.pen_width * 8
        # 每次喷洒的点数
        num_dots = 15
        
        for _ in range(num_dots):
            # 在喷洒半径内随机生成点
            angle = random.uniform(0, 2 * 3.14159)
            distance = random.uniform(0, spray_radius)
            
            x = int(self.current_spray_pos.x() + distance * random.uniform(-1, 1))
            y = int(self.current_spray_pos.y() + distance * random.uniform(-1, 1))
            
            # 确保点在画布范围内
            if 0 <= x < self.image.width() and 0 <= y < self.image.height():
                painter.drawPoint(x, y)
        
        painter.end()
        self.update()
        self.mark_content_modified()
            
    def clear_canvas(self):
        self.save_state()  # 操作前保存状态
        self.image.fill(Qt.white)
        self.update()
        self.mark_content_modified()
        
    def set_pen_color(self, color):
        self.pen_color = color
    
    def set_bg_color(self, color):
        self.bg_color = color
    
    def set_tool(self, tool):
        # 切换工具时提交当前矩形选区（如果有）
        if self.selection_active:
            self.commit_selection()
        
        # 切换工具时提交任意形状选区（如果有）
        if self.crop_selection_active:
            self.commit_crop_selection()
        
        # 切换工具时完成当前多边形绘制（如果有）
        if self.polygon_drawing:
            self.finish_polygon()
        
        # 切换工具时停止喷枪定时器
        if self.current_tool == "airbrush":
            self.airbrush_timer.stop()
            
        # 切换工具时完成文字输入（如果有）
        if self.is_text_mode and self.text_input_widget:
            self.finish_text_input()
        
        self.current_tool = tool

        # 设置鼠标光标形状
        if tool == "magnifier":
            self.setCursor(Qt.CrossCursor)
        else:
            self.unsetCursor()

        # 切换非文字工具时隐藏文字工具栏
        if tool != "text" and self.text_tool_dialog:
            self.text_tool_dialog.hide()
        
        # 更新文字工具栏菜单状态
        if hasattr(self, 'text_toolbar_action'):
            if tool == "text":
                # 文字工具时，菜单项可用
                self.text_toolbar_action.setEnabled(True)
                if self.text_tool_dialog and self.text_tool_dialog.isVisible():
                    self.text_toolbar_action.setChecked(True)
                else:
                    self.text_toolbar_action.setChecked(False)
            else:
                # 非文字工具时，菜单项灰色不可用且不带对勾
                self.text_toolbar_action.setEnabled(False)
                self.text_toolbar_action.setChecked(False)
    
    def set_pen_width(self, width):
        self.pen_width = width
    
    def set_pen_style(self, style_index):
        # 映射索引到线型
        styles = [Qt.SolidLine, Qt.DashLine, Qt.DotLine, Qt.DashDotLine, Qt.DashDotDotLine]
        if 0 <= style_index < len(styles):
            self.pen_style = styles[style_index]
    
    def set_polygon_fill_mode(self, mode):
        """设置多边形填充模式
        mode: "outline" (仅轮廓), "filled" (轮廓+填充), "fill_only" (仅填充)
        """
        self.polygon_fill_mode = mode
    
    def draw_shape(self, painter, start, end):
        """绘制各种形状"""
        if self.current_tool == "line":
            # 直线（不受填充模式影响）
            painter.drawLine(start, end)
            
        elif self.current_tool == "rectangle":
            # 矩形
            rect = QRect(start, end).normalized()
            self.draw_shape_with_fill_mode(painter, lambda p: p.drawRect(rect))
            
        elif self.current_tool == "ellipse":
            # 椭圆
            rect = QRect(start, end).normalized()
            self.draw_shape_with_fill_mode(painter, lambda p: p.drawEllipse(rect))
            
        elif self.current_tool == "rounded":
            # 圆角矩形
            rect = QRect(start, end).normalized()
            self.draw_shape_with_fill_mode(painter, lambda p: p.drawRoundedRect(rect, 20, 20))
    
    def draw_shape_with_fill_mode(self, painter, draw_func):
        """根据填充模式绘制形状"""
        # 保存原始的画笔和画刷
        original_pen = painter.pen()
        original_brush = painter.brush()
        
        if self.shape_fill_mode == "outline":
            # 模式1: 只有边框
            painter.setBrush(Qt.NoBrush)
            draw_func(painter)
        elif self.shape_fill_mode == "filled":
            # 模式2: 边框+填充（边框用当前颜色，填充用背景色）
            painter.setBrush(QBrush(self.bg_color))
            draw_func(painter)
        elif self.shape_fill_mode == "fill_only":
            # 模式3: 只有填充无边框（填充用当前颜色）
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(original_pen.color()))
            draw_func(painter)
        
        # 恢复原始的画笔和画刷
        painter.setPen(original_pen)
        painter.setBrush(original_brush)
    
    def flood_fill(self, pos):
        """填充工具 - 简单的颜色填充"""
        if not self.image.rect().contains(pos):
            return
        
        image = self.image.toImage()
        
        # 获取目标颜色
        target_color = image.pixelColor(pos.x(), pos.y())
        
        # 如果目标颜色和填充颜色相同，不需要填充
        if target_color == self.pen_color:
            return
        
        # 简单的区域填充
        self.fill_area_safe(image, pos, target_color)
        self.image = QPixmap.fromImage(image)
        self.update()
        self.mark_content_modified()
    
    def fill_area_safe(self, image, pos, target_color):
        """安全的填充区域（使用栈避免递归）"""
        width = image.width()
        height = image.height()
        
        # 使用栈避免递归深度问题
        stack = [pos]
        visited = set()
        
        while stack and len(visited) < 50000:  # 限制填充像素数
            current = stack.pop()
            x, y = current.x(), current.y()
            
            if (x, y) in visited:
                continue
            if x < 0 or x >= width or y < 0 or y >= height:
                continue
                
            pixel_color = image.pixelColor(x, y)
            if pixel_color != target_color:
                continue
            
            visited.add((x, y))
            image.setPixelColor(x, y, self.pen_color)
            
            # 添加四个方向的邻居
            stack.append(QPoint(x + 1, y))
            stack.append(QPoint(x - 1, y))
            stack.append(QPoint(x, y + 1))
            stack.append(QPoint(x, y - 1))
    
    def pick_color(self, pos):
        """取色器工具 - 获取点击位置的颜色"""
        if not self.image.rect().contains(pos):
            return
        
        image = self.image.toImage()
        color = image.pixelColor(pos.x(), pos.y())
        
        # 通知主窗口更新颜色
        try:
            # 获取主窗口
            parent = self.parent()
            while parent:
                if isinstance(parent, MSPaintWindow):
                    parent.change_fg_color(color.name())
                    break
                parent = parent.parent()
        except:
            pass
    
    def keyPressEvent(self, event):
        # 多边形工具的键盘支持
        if self.current_tool == "polygon" and self.polygon_drawing:
            if event.key() == Qt.Key_Escape:
                # ESC键取消多边形绘制
                self.cancel_polygon()
                return
            elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                # Enter键完成多边形（至少需要3个顶点）
                if len(self.polygon_points) >= 3:
                    self.finish_polygon()
                return
        
        # 文字工具的键盘支持
        if self.current_tool == "text" and self.is_text_mode:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                # 回车键完成输入
                if self.text_content:
                    painter = QPainter(self.image)
                    painter.setPen(QPen(self.pen_color, 1))
                    painter.setFont(self.text_font)
                    painter.drawText(self.text_start_point, self.text_content)
                    painter.end()
                    self.update()
                self.is_text_mode = False
                self.text_content = ""
            elif event.key() == Qt.Key_Backspace:
                # 退格键删除字符
                self.text_content = self.text_content[:-1]
                self.update()
            elif event.key() == Qt.Key_Escape:
                # ESC键取消输入
                self.is_text_mode = False
                self.text_content = ""
                self.update()
            else:
                # 添加字符
                self.text_content += event.text()
                self.update()
        else:
            super().keyPressEvent(event)
    
    def flip_image(self, direction):
        """翻转图像或选区"""
        self.save_state()  # 操作前保存状态
        # 如果有活动的选区，只对选区内容进行翻转
        if self.selection_active and self.selection_content is not None:
            transform = QTransform()
            
            if direction == "horizontal":
                transform.scale(-1, 1)
                transform.translate(-self.selection_content.width(), 0)
            elif direction == "vertical":
                transform.scale(1, -1)
                transform.translate(0, -self.selection_content.height())
            
            # 翻转选区内容
            self.selection_content = self.selection_content.transformed(transform)
        elif self.crop_selection_active and self.crop_selection_content is not None:
            transform = QTransform()
            
            if direction == "horizontal":
                transform.scale(-1, 1)
                transform.translate(-self.crop_selection_content.width(), 0)
            elif direction == "vertical":
                transform.scale(1, -1)
                transform.translate(0, -self.crop_selection_content.height())
            
            # 翻转任意形状选区内容
            self.crop_selection_content = self.crop_selection_content.transformed(transform)
        else:
            # 没有选区，翻转整个图像
            transform = QTransform()

            if direction == "horizontal":
                transform.scale(-1, 1)
                transform.translate(-self.image.width(), 0)
            elif direction == "vertical":
                transform.scale(1, -1)
                transform.translate(0, -self.image.height())

            self.image = self.image.transformed(transform)
        
        self.update()
        self.mark_content_modified()
    
    def rotate_image(self, angle):
        """旋转图像或选区"""
        self.save_state()  # 操作前保存状态
        # 如果有活动的选区，只对选区内容进行旋转
        if self.selection_active and self.selection_content is not None:
            # 创建变换矩阵
            transform = QTransform()

            # 获取选区内容矩形
            original_rect = self.selection_content.rect()

            # 先旋转
            transform.rotate(angle)
            rotated_rect = transform.mapRect(original_rect)

            # 创建新图像，使用透明背景填充
            new_image = QPixmap(rotated_rect.width(), rotated_rect.height())
            new_image.fill(Qt.transparent)

            # 绘制旋转后的选区内容
            painter = QPainter(new_image)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)

            # 重新创建变换，确保内容居中
            transform2 = QTransform()
            # 平移到新画布中心
            transform2.translate(rotated_rect.width() / 2, rotated_rect.height() / 2)
            # 旋转
            transform2.rotate(angle)
            # 平移到内容中心
            transform2.translate(-original_rect.width() / 2, -original_rect.height() / 2)

            painter.setTransform(transform2)
            painter.drawPixmap(0, 0, self.selection_content)
            painter.end()

            self.selection_content = new_image
            # 调整选区矩形大小以适应旋转后的内容
            self.selection_rect.setSize(rotated_rect.size())
            
        elif self.crop_selection_active and self.crop_selection_content is not None:
            # 旋转任意形状选区内容
            transform = QTransform()

            original_rect = self.crop_selection_content.rect()
            transform.rotate(angle)
            rotated_rect = transform.mapRect(original_rect)

            new_image = QPixmap(rotated_rect.width(), rotated_rect.height())
            new_image.fill(Qt.transparent)

            painter = QPainter(new_image)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)

            transform2 = QTransform()
            transform2.translate(rotated_rect.width() / 2, rotated_rect.height() / 2)
            transform2.rotate(angle)
            transform2.translate(-original_rect.width() / 2, -original_rect.height() / 2)

            painter.setTransform(transform2)
            painter.drawPixmap(0, 0, self.crop_selection_content)
            painter.end()

            self.crop_selection_content = new_image
            self.crop_selection_rect.setSize(rotated_rect.size())
            
        else:
            # 没有选区，旋转整个图像
            # 创建变换矩阵
            transform = QTransform()
            
            # 计算新图像尺寸
            original_rect = self.image.rect()
            
            # 先旋转
            transform.rotate(angle)
            rotated_rect = transform.mapRect(original_rect)
            
            # 创建新图像，使用当前背景色填充
            new_image = QPixmap(rotated_rect.width(), rotated_rect.height())
            new_image.fill(self.bg_color)
            
            # 绘制旋转后的图像
            painter = QPainter(new_image)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            
            # 重新创建变换，确保图像居中
            transform2 = QTransform()
            # 平移到新画布中心
            transform2.translate(rotated_rect.width() / 2, rotated_rect.height() / 2)
            # 旋转
            transform2.rotate(angle)
            # 平移到图像中心
            transform2.translate(-original_rect.width() / 2, -original_rect.height() / 2)
            
            painter.setTransform(transform2)
            painter.drawPixmap(0, 0, self.image)
            painter.end()
            
            self.image = new_image
            # 更新画布组件尺寸以匹配新图像大小（保持当前缩放）
            self._apply_zoom()
        
        self.update()
        self.mark_content_modified()
    
    def stretch_image(self, horizontal_percent, vertical_percent):
        """拉伸图像或选区"""
        self.save_state()  # 操作前保存状态
        # 如果有活动的选区，只对选区内容进行拉伸
        if self.selection_active and self.selection_content is not None:
            new_width = int(self.selection_content.width() * horizontal_percent / 100)
            new_height = int(self.selection_content.height() * vertical_percent / 100)
            
            # 拉伸选区内容
            self.selection_content = self.selection_content.scaled(new_width, new_height,
                                                                   Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            # 调整选区矩形大小
            self.selection_rect.setSize(self.selection_content.size())
            
        elif self.crop_selection_active and self.crop_selection_content is not None:
            new_width = int(self.crop_selection_content.width() * horizontal_percent / 100)
            new_height = int(self.crop_selection_content.height() * vertical_percent / 100)
            
            # 拉伸任意形状选区内容
            self.crop_selection_content = self.crop_selection_content.scaled(new_width, new_height,
                                                                               Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            # 调整选区矩形大小
            self.crop_selection_rect.setSize(self.crop_selection_content.size())
            
        else:
            # 没有选区，拉伸整个图像
            new_width = int(self.image.width() * horizontal_percent / 100)
            new_height = int(self.image.height() * vertical_percent / 100)
            
            self.image = self.image.scaled(new_width, new_height,
                                           Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        
        self.update()
        self.mark_content_modified()
    
    def skew_image(self, horizontal_angle, vertical_angle):
        """扭曲图像或选区"""
        self.save_state()  # 操作前保存状态
        # 如果有活动的选区，只对选区内容进行扭曲
        if self.selection_active and self.selection_content is not None:
            transform = QTransform()
            
            # 转换为弧度
            h_rad = horizontal_angle * 3.14159 / 180
            v_rad = vertical_angle * 3.14159 / 180
            
            # 应用剪切变换
            transform.shear(h_rad, v_rad)
            
            # 计算新选区内容尺寸
            original_rect = self.selection_content.rect()
            skewed_rect = transform.mapRect(original_rect)
            
            # 创建新图像，使用透明背景填充
            new_image = QPixmap(skewed_rect.width(), skewed_rect.height())
            new_image.fill(Qt.transparent)
            
            # 绘制扭曲后的选区内容
            painter = QPainter(new_image)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.setTransform(transform)
            painter.drawPixmap(0, 0, self.selection_content)
            painter.end()
            
            self.selection_content = new_image
            # 调整选区矩形大小以适应扭曲后的内容
            self.selection_rect.setSize(skewed_rect.size())
            
        elif self.crop_selection_active and self.crop_selection_content is not None:
            transform = QTransform()
            
            h_rad = horizontal_angle * 3.14159 / 180
            v_rad = vertical_angle * 3.14159 / 180
            
            transform.shear(h_rad, v_rad)
            
            original_rect = self.crop_selection_content.rect()
            skewed_rect = transform.mapRect(original_rect)
            
            new_image = QPixmap(skewed_rect.width(), skewed_rect.height())
            new_image.fill(Qt.transparent)
            
            painter = QPainter(new_image)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.setTransform(transform)
            painter.drawPixmap(0, 0, self.crop_selection_content)
            painter.end()
            
            self.crop_selection_content = new_image
            self.crop_selection_rect.setSize(skewed_rect.size())
            
        else:
            # 没有选区，扭曲整个图像
            transform = QTransform()
            
            # 转换为弧度
            h_rad = horizontal_angle * 3.14159 / 180
            v_rad = vertical_angle * 3.14159 / 180
            
            # 应用剪切变换
            transform.shear(h_rad, v_rad)
            
            # 计算新图像尺寸
            original_rect = self.image.rect()
            skewed_rect = transform.mapRect(original_rect)
            
            # 创建新图像
            new_image = QPixmap(skewed_rect.width(), skewed_rect.height())
            new_image.fill(Qt.white)
            
            # 绘制扭曲后的图像
            painter = QPainter(new_image)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            painter.setTransform(transform)
            painter.drawPixmap(0, 0, self.image)
            painter.end()
            
            self.image = new_image
        
        self.update()
        self.mark_content_modified()

    def invert_colors(self):
        """反色功能：如果没有选区，反色整个画布；如果有选区，只反色选区内容"""
        self.save_state()  # 操作前保存状态
        # 检查是否有活动的矩形选区
        if self.selection_active and self.selection_content is not None:
            # 反色矩形选区内容
            img = self.selection_content.toImage()
            for x in range(img.width()):
                for y in range(img.height()):
                    color = img.pixelColor(x, y)
                    inverted_color = QColor(255 - color.red(), 255 - color.green(), 255 - color.blue())
                    img.setPixelColor(x, y, inverted_color)
            self.selection_content = QPixmap.fromImage(img)
            self.update()
            self.mark_content_modified()
            return
        
        # 检查是否有活动的任意形状选区
        if self.crop_selection_active and self.crop_selection_content is not None:
            # 反色任意形状选区内容
            img = self.crop_selection_content.toImage()
            for x in range(img.width()):
                for y in range(img.height()):
                    color = img.pixelColor(x, y)
                    inverted_color = QColor(255 - color.red(), 255 - color.green(), 255 - color.blue())
                    img.setPixelColor(x, y, inverted_color)
            self.crop_selection_content = QPixmap.fromImage(img)
            self.update()
            self.mark_content_modified()
            return
        
        # 没有选区，反色整个画布
        img = self.image.toImage()
        for x in range(img.width()):
            for y in range(img.height()):
                color = img.pixelColor(x, y)
                inverted_color = QColor(255 - color.red(), 255 - color.green(), 255 - color.blue())
                img.setPixelColor(x, y, inverted_color)
        self.image = QPixmap.fromImage(img)
        self.update()
        self.mark_content_modified()


class MSPaintWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def load_ai_config(self):
        """从paint.ini配置文件加载AI设置，支持多模型配置"""
        config_dir = os.path.expanduser("~/.config/paintai")
        os.makedirs(config_dir, exist_ok=True)
        config_file = os.path.join(config_dir, 'paint.ini')
        
        config = configparser.ConfigParser()
        
        try:
            if os.path.exists(config_file):
                # 读取现有配置文件
                config.read(config_file, encoding='utf-8')
                
                # 获取当前选中的模型
                current_model = '豆包-Seedream'
                if 'GLOBAL' in config and 'current_model' in config['GLOBAL']:
                    current_model = config['GLOBAL']['current_model']
                
                # 获取当前模型的配置
                model_section = current_model.replace(' ', '_').replace('-', '_')
                if model_section in config:
                    settings = {}
                    model_config = config[model_section]
                    
                    # 读取模型特定配置
                    for key in ['api_base_url', 'image_endpoint', 'model_name', 'api_key',
                               'image_size', 'quality', 'style', 'description']:
                        settings[key] = model_config.get(key, '')
                    
                    # 读取数值配置
                    settings['timeout'] = model_config.getint('timeout', 60)
                    settings['n'] = model_config.getint('n', 1)
                    settings['max_tokens'] = model_config.getint('max_tokens', 2048)
                    settings['temperature'] = model_config.getint('temperature', 70)
                    settings['quality_level'] = model_config.getint('quality_level', 7)
                    
                    # 读取全局设置
                    if 'GLOBAL' in config:
                        global_config = config['GLOBAL']
                        settings['auto_apply'] = global_config.getboolean('auto_apply', True)
                        settings['custom_size'] = global_config.get('custom_size', '')
                    else:
                        settings['auto_apply'] = True
                        settings['custom_size'] = ''
                    
                    # 添加模型名称
                    settings['model'] = current_model
                    
                    return settings
                else:
                    # 配置文件存在但没有当前模型的配置，创建所有模型的配置
                    self.create_all_models_config()
                    # 重新加载配置
                    return self.load_ai_config()
            else:
                # 配置文件不存在，创建所有模型的配置
                self.create_all_models_config()
                # 重新加载配置
                return self.load_ai_config()
                
        except Exception as e:
            print(f"读取配置文件失败: {e}")
            # 如果读取失败，返回豆包默认配置
            return get_model_config('豆包-Seedream')
    
    def create_all_models_config(self):
        """创建包含所有模型配置的完整配置文件"""
        config_dir = os.path.expanduser("~/.config/paintai")
        os.makedirs(config_dir, exist_ok=True)
        config_file = os.path.join(config_dir, 'paint.ini')
        config = configparser.ConfigParser()
        
        try:
            # 创建全局配置部分
            config.add_section('GLOBAL')
            config.set('GLOBAL', 'current_model', '豆包-Seedream')
            config.set('GLOBAL', 'auto_apply', 'True')
            config.set('GLOBAL', 'custom_size', '')
            
            # 为每个模型创建配置部分
            for model_name, model_config in AI_MODEL_CONFIGS.items():
                model_section = model_name.replace(' ', '_').replace('-', '_')
                config.add_section(model_section)
                
                # 保存模型特定配置
                model_keys = ['api_base_url', 'image_endpoint', 'model_name', 'api_key',
                             'timeout', 'image_size', 'n', 'quality', 'style',
                             'max_tokens', 'temperature', 'quality_level', 'description']
                
                for key in model_keys:
                    if key in model_config:
                        config.set(model_section, key, str(model_config[key]))
            
            # 写入配置文件
            with open(config_file, 'w', encoding='utf-8') as f:
                config.write(f)
                
            print(f"已创建包含 {len(AI_MODEL_CONFIGS)} 个模型的完整配置文件: {config_file}")
            
        except Exception as e:
            print(f"创建完整配置文件失败: {e}")
    
    def save_ai_config(self, settings, current_model=None):
        """保存AI设置到paint.ini配置文件，支持多模型配置"""
        config_dir = os.path.expanduser("~/.config/paintai")
        os.makedirs(config_dir, exist_ok=True)
        config_file = os.path.join(config_dir, 'paint.ini')
        config = configparser.ConfigParser()
        
        try:
            # 如果配置文件已存在，先读取现有配置
            if os.path.exists(config_file):
                config.read(config_file, encoding='utf-8')
            
            # 获取当前模型名称
            if current_model is None:
                current_model = settings.get('model', '豆包-Seedream')
            
            # 创建全局配置部分
            if 'GLOBAL' not in config:
                config.add_section('GLOBAL')
            
            # 保存当前选中的模型
            config.set('GLOBAL', 'current_model', current_model)
            config.set('GLOBAL', 'auto_apply', str(settings.get('auto_apply', True)))
            config.set('GLOBAL', 'custom_size', str(settings.get('custom_size', '')))
            
            # 创建模型特定的配置部分
            model_section = current_model.replace(' ', '_').replace('-', '_')
            if model_section not in config:
                config.add_section(model_section)
            
            # 保存模型特定配置
            model_keys = ['api_base_url', 'image_endpoint', 'model_name', 'api_key',
                         'timeout', 'image_size', 'n', 'quality', 'style',
                         'max_tokens', 'temperature', 'quality_level', 'description']
            
            for key in model_keys:
                if key in settings:
                    config.set(model_section, key, str(settings[key]))
            
            # 写入配置文件
            with open(config_file, 'w', encoding='utf-8') as f:
                config.write(f)
                
            print(f"AI配置已保存到 {config_file}，当前模型: {current_model}")
            
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def init_ui(self):
        self.setWindowTitle("未命名 - 画图")
        self.setGeometry(100, 100, 1000, 700)
        
        # 加载AI设置（从配置文件或默认值）
        self.ai_settings = self.load_ai_config()
        
        # 初始化文件操作相关属性
        self.current_file_path = None  # 当前文件路径
        
        # 初始化文字工具对话框
        self.text_tool_dialog = None
        
        # 先初始化画布（在创建菜单栏之前）
        self.canvas = PaintCanvas()
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 左侧工具栏
        self.toolbox_widget = self.create_toolbox(main_layout)
        
        # 中间区域（画布 + 颜色选择 + 状态栏）
        middle_widget = QWidget()
        middle_layout = QVBoxLayout(middle_widget)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)
        
        # 画布滚动区域
        scroll_area = QScrollArea()
        scroll_area.setStyleSheet("background-color: #C0C0C0;")
        scroll_area.setWidget(self.canvas)
        scroll_area.setWidgetResizable(False)
        middle_layout.addWidget(scroll_area, stretch=1)
        
        # 颜色选择器和笔刷设置
        self.color_palette_widget = self.create_color_palette_and_brush(middle_layout)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.status_bar.showMessage('按住 Shift 键并拖动"帮助"来查找主题。单击"帮助主题"。')
        self.status_bar.setStyleSheet("background-color: #D4D0C8; color: black;")
        middle_layout.addWidget(self.status_bar)
        
        main_layout.addWidget(middle_widget, stretch=1)
        
        # 设置窗口关闭事件处理
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        # 创建定时器来同步文字工具栏菜单状态
        self.text_toolbar_sync_timer = QTimer()
        self.text_toolbar_sync_timer.timeout.connect(self.sync_text_toolbar_menu_state)
        self.text_toolbar_sync_timer.start(500)  # 每500毫秒同步一次
    
    def closeEvent(self, event):
        """窗口关闭事件处理"""
        # 先完成文字输入（如果有）
        if self.canvas.is_text_mode:
            self.canvas.finish_text_input()
        
        # 关闭文字工具栏
        if self.canvas.text_tool_dialog:
            self.canvas.text_tool_dialog.close()
            self.canvas.text_tool_dialog = None
        
        if self.canvas.is_content_modified():
            reply = QMessageBox.question(
                self,
                "保存更改",
                "画布内容已更改。\n\n是否保存更改？",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )
            
            if reply == QMessageBox.Save:
                # 尝试保存文件
                if not self.save_current_file():
                    # 如果保存失败或被取消，阻止关闭
                    event.ignore()
                    return
            elif reply == QMessageBox.Cancel:
                # 取消关闭
                event.ignore()
                return
            # 如果选择的是Discard，则直接关闭
        
        # 如果没有修改或用户选择不保存，则正常关闭
        event.accept()
    
    def save_current_file(self):
        """保存当前文件"""
        try:
            # 这里可以实现实际的文件保存逻辑
            # 暂时使用文件对话框让用户选择保存位置
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存图像",
                "",
                "PNG Files (*.png);;JPEG Files (*.jpg *.jpeg);;BMP Files (*.bmp);;All Files (*)"
            )
            
            if file_path:
                # 保存图像
                self.canvas.image.save(file_path)
                # 重置修改标志
                self.canvas.reset_content_modified_flag()
                return True
            else:
                # 用户取消了保存
                return False
                
        except Exception as e:
            QMessageBox.critical(self, "保存错误", f"保存文件时发生错误：\n{str(e)}")
            return False
    
    def edit_cut(self):
        """剪切操作"""
        if self.canvas.cut_selection():
            self.statusBar().showMessage("已剪切选区内容", 2000)
        else:
            QMessageBox.information(self, "提示", "没有活动的选区")
    
    def edit_copy(self):
        """复制操作"""
        if self.canvas.copy_selection():
            self.statusBar().showMessage("已复制选区内容", 2000)
        else:
            QMessageBox.information(self, "提示", "没有活动的选区")
    
    def edit_paste(self):
        """粘贴操作"""
        if self.canvas.paste_from_clipboard():
            self.statusBar().showMessage("已粘贴剪贴板内容", 2000)
        else:
            QMessageBox.information(self, "提示", "剪贴板中没有图像内容")
    
    def select_all(self):
        """全选 - 建立与当前画布一样大的选区"""
        if self.canvas.image.isNull():
            QMessageBox.information(self, "提示", "画布为空，无法建立选区")
            return
        
        # 创建覆盖整个画布的选区
        self.canvas.selection_rect = QRect(0, 0, self.canvas.image.width(), self.canvas.image.height())
        self.canvas.selection_content = self.canvas.image.copy(self.canvas.selection_rect)
        self.canvas.selection_active = True
        self.canvas.update()
        self.statusBar().showMessage("已选择整个画布", 2000)
    
    def clear_selection_area(self):
        """清除选区内的内容"""
        if not self.canvas.selection_active:
            QMessageBox.information(self, "提示", "没有活动的选区")
            return
        
        # 清除选区内的内容（用背景色填充）
        painter = QPainter(self.canvas.image)
        painter.setBrush(self.canvas.bg_color)
        painter.setPen(Qt.NoPen)
        painter.drawRect(self.canvas.selection_rect)
        painter.end()
        
        # 清除选区状态
        self.canvas.clear_selection()
        self.canvas.mark_content_modified()
        self.canvas.update()
        self.statusBar().showMessage("已清除选区内容", 2000)
    
    def print_image(self):
        """打印当前图像"""
        if self.canvas.image.isNull():
            QMessageBox.information(self, "提示", "没有可打印的图像")
            return
        
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPrinter.A4)
        printer.setOrientation(QPrinter.Portrait)
        
        print_dialog = QPrintDialog(printer, self)
        if print_dialog.exec_() == QPrintDialog.Accepted:
            try:
                painter = QPainter(printer)
                painter.setRenderHint(QPainter.Antialiasing)
                
                # 获取打印机的页面矩形
                page_rect = printer.pageRect()
                
                # 获取图像尺寸
                image_size = self.canvas.image.size()
                
                # 计算缩放比例，使图像适应页面，保持宽高比
                scale_x = page_rect.width() / image_size.width()
                scale_y = page_rect.height() / image_size.height()
                scale = min(scale_x, scale_y)
                
                # 计算居中位置
                scaled_width = int(image_size.width() * scale)
                scaled_height = int(image_size.height() * scale)
                x = (page_rect.width() - scaled_width) // 2
                y = (page_rect.height() - scaled_height) // 2
                
                # 绘制图像
                painter.drawPixmap(x, y, scaled_width, scaled_height, self.canvas.image)
                painter.end()
                
                self.statusBar().showMessage("打印完成", 2000)
            except Exception as e:
                QMessageBox.critical(self, "打印错误", f"打印失败：{str(e)}")
    
    def print_preview(self):
        """打印预览"""
        if self.canvas.image.isNull():
            QMessageBox.information(self, "提示", "没有可预览的图像")
            return
        
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPrinter.A4)
        printer.setOrientation(QPrinter.Portrait)
        
        preview_dialog = QPrintPreviewDialog(printer, self)
        preview_dialog.setWindowTitle("打印预览")
        preview_dialog.setWindowState(Qt.WindowMaximized)
        
        # 连接预览对话框的paintRequested信号
        preview_dialog.paintRequested.connect(lambda: self.handle_print_preview(printer))
        
        preview_dialog.exec_()
    
    def handle_print_preview(self, printer):
        """处理打印预览的绘制"""
        try:
            painter = QPainter(printer)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 获取打印机的页面矩形
            page_rect = printer.pageRect()
            
            # 获取图像尺寸
            image_size = self.canvas.image.size()
            
            # 计算缩放比例，使图像适应页面，保持宽高比
            scale_x = page_rect.width() / image_size.width()
            scale_y = page_rect.height() / image_size.height()
            scale = min(scale_x, scale_y)
            
            # 计算居中位置
            scaled_width = int(image_size.width() * scale)
            scaled_height = int(image_size.height() * scale)
            x = (page_rect.width() - scaled_width) // 2
            y = (page_rect.height() - scaled_height) // 2
            
            # 绘制图像
            painter.drawPixmap(x, y, scaled_width, scaled_height, self.canvas.image)
            painter.end()
        except Exception as e:
            QMessageBox.critical(self, "预览错误", f"预览失败：{str(e)}")
        
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar { 
                background-color: #ECE9D8; 
                color: black;
                border-bottom: 1px solid #808080;
            }
            QMenuBar::item:selected { 
                background-color: #316AC5;
                color: white;
            }
        """)
        
        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        new_action = file_menu.addAction("新建")
        new_action.triggered.connect(self.new_file)
        
        open_action = file_menu.addAction("打开")
        open_action.triggered.connect(self.open_file)
        
        save_action = file_menu.addAction("保存")
        save_action.triggered.connect(self.save_file)
        
        save_as_action = file_menu.addAction("另存为")
        save_as_action.triggered.connect(self.save_as_file)
        file_menu.addSeparator()
        self.ai_generate_action = file_menu.addAction("AI生成")
        self.ai_generate_action.triggered.connect(self.show_ai_generate_dialog)
        self.ai_setup_action = file_menu.addAction("AI设置")
        self.ai_setup_action.triggered.connect(self.show_ai_setup_dialog)
        file_menu.addSeparator()
        print_action = file_menu.addAction("打印")
        print_action.setShortcut("Ctrl+P")
        print_action.triggered.connect(self.print_image)
        print_preview_action = file_menu.addAction("打印预览")
        print_preview_action.triggered.connect(self.print_preview)
        file_menu.addSeparator()
        file_menu.addAction("最近用文件")
        file_menu.addSeparator()
        exit_action = file_menu.addAction("退出")
        exit_action.triggered.connect(self.close)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑(&E)")
        
        # 撤销功能
        self.undo_action = edit_menu.addAction("撤销")
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.triggered.connect(self.canvas.undo)
        
        # 重做功能
        self.redo_action = edit_menu.addAction("重做")
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.triggered.connect(self.canvas.redo)
        
        edit_menu.addSeparator()
        
        # 剪切复制粘贴功能
        cut_action = edit_menu.addAction("剪切")
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(self.edit_cut)
        
        copy_action = edit_menu.addAction("复制")
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.edit_copy)
        
        paste_action = edit_menu.addAction("粘贴")
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self.edit_paste)
        
        edit_menu.addSeparator()
        select_all_action = edit_menu.addAction("全选")
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self.select_all)
        
        clear_selection_action = edit_menu.addAction("清空选区")
        clear_selection_action.triggered.connect(self.clear_selection_area)
        
        clear_action = edit_menu.addAction("清空画布")
        clear_action.triggered.connect(self.canvas.clear_canvas)
        
        # 查看菜单
        view_menu = menubar.addMenu("查看(&V)")
        
        # 工具箱开关菜单项
        self.toolbox_action = view_menu.addAction("工具箱")
        self.toolbox_action.setCheckable(True)
        self.toolbox_action.setChecked(True)
        self.toolbox_action.triggered.connect(self.toggle_toolbox)
        
        # 颜色盒开关菜单项
        self.color_palette_action = view_menu.addAction("颜色盒")
        self.color_palette_action.setCheckable(True)
        self.color_palette_action.setChecked(True)
        self.color_palette_action.triggered.connect(self.toggle_color_palette)
        
        # 状态栏开关菜单项
        self.status_bar_action = view_menu.addAction("状态栏")
        self.status_bar_action.setCheckable(True)
        self.status_bar_action.setChecked(True)
        self.status_bar_action.triggered.connect(self.toggle_status_bar)
        
        # 文字工具栏开关菜单项
        self.text_toolbar_action = view_menu.addAction("文字工具栏")
        self.text_toolbar_action.setCheckable(True)
        self.text_toolbar_action.setChecked(False)
        self.text_toolbar_action.triggered.connect(self.toggle_text_toolbar)
        
        # 初始状态：文字工具栏菜单项始终可用
        self.text_toolbar_action.setEnabled(True)

        
        # 图像菜单
        image_menu = menubar.addMenu("图像(&I)")
        
        # 翻转/旋转菜单项
        flip_rotate_action = image_menu.addAction("翻转/旋转")
        flip_rotate_action.triggered.connect(self.show_flip_rotate_dialog)
        
        # 拉伸/扭曲菜单项
        stretch_skew_action = image_menu.addAction("拉伸/扭曲")
        stretch_skew_action.triggered.connect(self.show_stretch_skew_dialog)
        
        invert_colors_action = image_menu.addAction("反色")
        invert_colors_action.triggered.connect(self.invert_colors)

        # 图像属性菜单项
        properties_action = image_menu.addAction("属性")
        properties_action.triggered.connect(self.show_image_properties)
        
        # 颜色菜单
        color_menu = menubar.addMenu("颜色(&C)")
        edit_colors_action = color_menu.addAction("编辑颜色(&E)...")
        edit_colors_action.triggered.connect(self.edit_colors)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        help_menu.addAction("帮助主题")
        self.about_action = help_menu.addAction("关于画图")
        self.about_action.triggered.connect(self.about_paint)
        
    def about_paint(self):
        """关于画图 - 显示捐赠信息对话框"""
        dialog = AboutDonationDialog(self)
        dialog.exec_()
        
    def create_toolbox(self, main_layout):
        """创建左侧工具箱"""
        toolbox = QWidget()
        toolbox.setFixedWidth(60)
        toolbox.setStyleSheet("background-color: #D4D0C8; border-right: 1px solid #808080;")
        
        toolbox_layout = QVBoxLayout(toolbox)
        toolbox_layout.setContentsMargins(4, 4, 4, 4)
        toolbox_layout.setSpacing(2)
        
        # 工具按钮网格
        tools_grid = QGridLayout()
        tools_grid.setSpacing(2)
        
        tool_style = """
            QPushButton {
                background-color: #D4D0C8;
                border: 1px solid #808080;
                border-radius: 0px;
                min-width: 24px;
                max-width: 24px;
                min-height: 24px;
                max-height: 24px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #E8E5D8;
            }
            QPushButton:pressed, QPushButton:checked {
                background-color: #C0C0C0;
                border: 2px inset #404040;
            }
        """
        
        # 工具列表（按新顺序排列）
        tools = [
            ("crop", "任意形状选择", self.create_icon("crop")),
            ("select", "矩形选取", self.create_icon("select")),
            ("eraser", "橡皮", self.create_icon("eraser")),
            ("fill", "填充", self.create_icon("fill")),
            ("eyedropper", "取色", self.create_icon("eyedropper")),
            ("magnifier", "放大", self.create_icon("magnifier")),
            ("pencil", "铅笔", self.create_icon("pencil")),
            ("brush", "刷子", self.create_icon("brush")),
            ("airbrush", "喷枪", self.create_icon("airbrush")),
            ("text", "文字", self.create_icon("text")),
            ("line", "直线", self.create_icon("line")),
            ("curve", "曲线", self.create_icon("curve")),
            ("rectangle", "矩形", self.create_icon("rectangle")),
            ("polygon", "任意多边形", self.create_icon("polygon")),
            ("ellipse", "椭圆", self.create_icon("ellipse")),
            ("rounded", "圆角矩形", self.create_icon("rounded"))
        ]
        
        self.tool_buttons = []
        
        for i, (tool_name, tooltip, icon) in enumerate(tools):
            btn = QPushButton()
            btn.setIcon(icon)
            btn.setStyleSheet(tool_style)
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            
            # 默认选中铅笔工具
            if tool_name == "pencil":
                btn.setChecked(True)
            
            btn.clicked.connect(lambda checked, t=tool_name, b=btn: self.select_tool(t, b))
            self.tool_buttons.append(btn)
            tools_grid.addWidget(btn, i // 2, i % 2)
        
        toolbox_layout.addLayout(tools_grid)
        
        # 添加撤销/重做按钮
        undo_redo_widget = QWidget()
        undo_redo_layout = QHBoxLayout(undo_redo_widget)
        undo_redo_layout.setContentsMargins(2, 2, 2, 2)
        undo_redo_layout.setSpacing(2)
        
        # 撤销按钮
        self.undo_btn = QPushButton("↶")
        self.undo_btn.setToolTip("撤销 (Ctrl+Z)")
        self.undo_btn.setStyleSheet(tool_style)
        self.undo_btn.clicked.connect(self.canvas.undo)
        undo_redo_layout.addWidget(self.undo_btn)
        
        # 重做按钮
        self.redo_btn = QPushButton("↷")
        self.redo_btn.setToolTip("重做 (Ctrl+Y)")
        self.redo_btn.setStyleSheet(tool_style)
        self.redo_btn.clicked.connect(self.canvas.redo)
        undo_redo_layout.addWidget(self.redo_btn)
        
        toolbox_layout.addWidget(undo_redo_widget)
        
        # 添加填充模式选择器
        mode_label = QLabel(":")
        mode_label.setStyleSheet("color: black; font-size: 9px;")
        toolbox_layout.addWidget(mode_label)
        self.mode_label = mode_label  # 保存引用
        
        # 创建三个模式按钮
        mode_widget = QWidget()
        mode_layout = QVBoxLayout(mode_widget)
        mode_layout.setContentsMargins(2, 2, 2, 2)
        mode_layout.setSpacing(2)
        self.mode_widget = mode_widget  # 保存引用
        
        mode_button_style = """
            QPushButton {
                background-color: #D4D0C8;
                border: 1px solid #808080;
                min-width: 48px;
                max-width: 48px;
                min-height: 20px;
                max-height: 20px;
            }
            QPushButton:hover {
                background-color: #E8E5D8;
            }
            QPushButton:checked {
                background-color: #C0C0C0;
                border: 2px inset #404040;
            }
        """
        
        self.mode_buttons = []
        
        # 模式1: 只有边框
        mode1_btn = QPushButton()
        mode1_btn.setIcon(self.create_mode_icon("outline"))
        mode1_btn.setToolTip("仅边框")
        mode1_btn.setCheckable(True)
        mode1_btn.setChecked(True)  # 默认选中
        mode1_btn.setStyleSheet(mode_button_style)
        mode1_btn.clicked.connect(lambda: self.set_fill_mode("outline", mode1_btn))
        mode_layout.addWidget(mode1_btn)
        self.mode_buttons.append(mode1_btn)
        
        # 模式2: 边框加填充
        mode2_btn = QPushButton()
        mode2_btn.setIcon(self.create_mode_icon("filled"))
        mode2_btn.setToolTip("边框+填充")
        mode2_btn.setCheckable(True)
        mode2_btn.setStyleSheet(mode_button_style)
        mode2_btn.clicked.connect(lambda: self.set_fill_mode("filled", mode2_btn))
        mode_layout.addWidget(mode2_btn)
        self.mode_buttons.append(mode2_btn)
        
        # 模式3: 只有填充
        mode3_btn = QPushButton()
        mode3_btn.setIcon(self.create_mode_icon("fill_only"))
        mode3_btn.setToolTip("仅填充")
        mode3_btn.setCheckable(True)
        mode3_btn.setStyleSheet(mode_button_style)
        mode3_btn.clicked.connect(lambda: self.set_fill_mode("fill_only", mode3_btn))
        mode_layout.addWidget(mode3_btn)
        self.mode_buttons.append(mode3_btn)
        
        toolbox_layout.addWidget(mode_widget)
        toolbox_layout.addStretch()
        
        # 初始隐藏填充模式选择器（默认工具是铅笔，不需要填充模式）
        mode_label.hide()
        mode_widget.hide()
        
        main_layout.addWidget(toolbox)
        return toolbox
    
    def create_icon(self, tool_name):
        """根据工具名称创建图标"""
        # 简单的Base64图标数据 - 16x16像素
        icon_data = {
            "select": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsSAAALEgHS3X78AAAAQElEQVQ4T2NgoBK4CjXnP5AGYRAghn2VBc0BjEh8YthUcj/QGJgXSDXxKhOpOmimftQLiKAlJvUhq6FZpAwlgwE4RRanfEMhnAAAAABJRU5ErkJggg==",
            "crop": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsSAAALEgHS3X78AAAAdElEQVQ4T51Q2w2AIBA7XYf9RzFxBRN3EEkU60FJD77uUfo4s/ZdnRkdrWQzIvntGMEyQdz9gmpyNA8c9iwC2mFxIrfWsUpOitl0HWuwinLlP4893U39U4q3wRoNFUWPYdiP+WEIuQucgUPR6hQhzaayhTJnFM0iQ4vipPIAAAAASUVORK5CYII=",
            "pencil": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsSAAALEgHS3X78AAAAmklEQVQ4T6VS2w2AIAykxmlkCd3VPeTXARjDGWoLqDVBKNiEEE3vUXpgdIWiDSRkVOD9JpoWYzx92utXkQARLQBM3DxjMgEvA1V9VkNyQFyBga9bvYhOjQwLwHSYUF2ewVzOuV71YLxXPYJ/qD8PR0M3zb52z56ed4/r6pudOQ6xNhnh7PpysfrMfY5hKKSiLbOCqGpbHUVN4wnChnL5OZeo3QAAAABJRU5ErkJggg==",
            "fill": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsSAAALEgHS3X78AAAAqUlEQVQ4T71T2xGAMAhDJ6uT2yV0nQpUavCorw+58yzPJFiJfrCFMcpXnCJ2NWCEyXkvlLfY3qsH9fkRNqEZSsk56xkN/TObAQPcTCklonmOYaYJ49JLTcLLZpN0DGijDQXRPHItrSyLk8ABpaWyTEa/mYhz+BVQ36rOTbMA9hg0jW6bnpVfYrB2k4OajVXLiQRf6CfVXIB8Bry775Lv3kIb9vmHCeQ/D23ipFYrkNVMygAAAABJRU5ErkJggg==",
            "brush": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAC4jAAAuIwF4pT92AAAAs0lEQVQ4T2NgwA82AaVBmCyQuX8/w38QBurOxGUCEx6jTZHkkNkoWvAZYIekEplN2IA3L28wAlUpI6lUhophOBiXC7ixeA2bGAMuA0SxGIBNjAHkVGwAFPoowNERzMVQj80FKeiaQTqhYvHotrFgsV4Xahs2l6mhC2JzgQmetKFLTJL8jwsANT/BawAwrkFeAutvaGhAoUEckBwhL/AQ40RkNehhIEKqAejxiuFELAai6AEATgJKjm/3q0sAAAAASUVORK5CYII=",
            "airbrush": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAC4jAAAuIwF4pT92AAAAr0lEQVQ4T82S6w3CMAyEXdZhiTAzA8QdohITICGxg8mlOZJSNwoSP7Bk2XJ8X5yHyB9ZtHWYaM/H7QwveegNOVGkOkkIJoxVdGE6p8SDRVPVtHuNRYGJjIa8uDfQTowmR2wJAt+YK0bHHYS6M8XvWktxIdetGEdwIYcT5GMMQzpP1YGIndbbx2vyH+xQ5alRRwoeYi5z7VDc0ppJMoU2JGbzkhL4p30F+am4c/eDSy+xGJ8pXwSwcAAAAABJRU5ErkJggg==",
            "eyedropper": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsSAAALEgHS3X78AAAAlElEQVQ4T82S3Q2AIAyEW9fRJdiMzcoSJq5g4g7Ij0BVwPJmEyPBfnftRYTxsgzBaZC3xhiOcLG21LFvs/vqm18PCiboukgEvEdLRJSBdVUbNJh/hZhhrXUWcZksgtXBw6EcnMLrrXPTbMES4+IMRNz513Aa1b+fZ6K1NzteAIBSpY/ozShV/eniZXStVwMUJSppOgE4z3RxVHvvwwAAAABJRU5ErkJggg==",
            "magnifier": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsSAAALEgHS3X78AAAA6klEQVQ4T6WT3w3CIBDGizM06QrG+uYAwGbtW1fRJaQD+NjGDYyJO+B9FAilUEO8hIfen99d+Q5WbU1HLpbI8a4wOJH3pJRa5Qsh8D3TafdAU9d1OjQCaXcQo2I02JibALUmOI5jshEm+byf57o5rkAHykan3WIEkUPFQ0wHoMQuWUBu9F/00gkeMdBfYixfmMg5rxgzqZudcBPMOQCK+743PJIzKaVrhqDXHjsAW3bg7g9JmV8oG7zZpcFimELAQkj4e7t7boFt3byuSrFKiPCZyPSl5GXDJCsIvQ/ZFsgoGSYA5E9zF7pgvvLehF/WBat/AAAAAElFTkSuQmCC",
            "eraser": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsSAAALEgHS3X78AAAAmUlEQVQ4T2NgGGjASIQDlgDVqAKxClTtHSB9G4hjiNDL8B8CMGmg5s2EDMCn+T9Q8zOQAUw4TAFby8AA8iEqzQgU2r8foQubAcRqPgsyBj0QidLs6Ah2AVgvsgEka0Y24AAQ2GMLDwcHB7ifkW2GqYWFAVbNyAZi04wcCwfxxSkuzehhsAAooADF8kD6IRA/gOIEQolmCMsDAMleXUdLOM08AAAAAElFTkSuQmCC",
            "text": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAC4jAAAuIwF4pT92AAAAgElEQVQ4T2NgGOzgPyEHMuFRcAAqd5WQIbjkQbaD8ZuXN7RJMgSowQGmGUqT7AqYBtJdAXUuzAAQDTOEaFesgvkZSpPsCnSb4AYAXUOUK5A1YLAJxchVJOcLA9nmQBxDSoyA4jwMR5wjuwauhBHKQk+yMHGQNL7kjKyOpLRGPcUAOnZR/GVZCF8AAAAASUVORK5CYII=",
            "line": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAC4jAAAuIwF4pT92AAAAK0lEQVQ4T2NgGCzgP9AhVyl1DMgQEKYIjBqCGXyjYTKYwwSUbyhO9mAPAgCSDBmTPPStbQAAAABJRU5ErkJggg==",
            "curve": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAC4jAAAuIwF4pT92AAAAX0lEQVQ4T2NgoDH4DzT/KqV2gAwBYYoAyIDNZJvw5uUNbaDmZ9gMYCLbVBI1UuQFigJx4DSDooyiuH8GjTqCYU2zaKTYCyCnExUDjAQ8CQ5IYHgkAqkHICwirgGi4QAAZ/shFAZOUXQAAAAASUVORK5CYII=",
            "polygon": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAC4jAAAuIwF4pT92AAAApUlEQVQ4T8VT2Q2AIAwF4wgmrmDUHWQ0R2MJjSuYuIMWFAJNC+iPftJ39VCIvz/JBDgLglluzQG11mRJKSWOfRubtrP1CqOgqDLuK5AXh6FaWMC9p0QCdy8QJQD3AYgk+RGM3M0bTvDKPZrBF3ecAFrXE9c7kdZCwzWmyAZL3Ya0AmZ1bq84Qeoe/AyAPHPA3EW6NZLxc+RwiCW3T+lx/1KJ9425ACcANsQ4yEzcAAAAAElFTkSuQmCC",
            "rectangle": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAC4jAAAuIwF4pT92AAAANElEQVQ4T2NgGGjACHXAf3IdwgLTeODAAZLNcHBwYGAiWReahlEDGIZDIFKcEilNR4NAPwBYrgUVSH79ogAAAABJRU5ErkJggg==",
            "ellipse": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAC4jAAAuIwF4pT92AAAAdElEQVQ4T2NgGH7gzcsb2kBfLQDiA0D8AIj/Q2kQfwFUHu5xRrQguArkax04AFKLHTg4OIAkrgExyCIGZAP+49OIbhzUIEYmqMRmUjSD9EDV/4cZYExubMIMIFc/A8yAs+SaQHEgUhyNGC4nNSGR6/VBpA8A+TUvnSgW7w4AAAAASUVORK5CYII=",
            "rounded": "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAC4jAAAuIwF4pT92AAAAXklEQVQ4T2NgGPKAEc0HU4F8USAWg9IgNgi/RsKvoOxskF5kA/4fOHCA6BBxcHAA62eC6lhAimaQHqj6/zADFIi2Gk0h1QyQp9QFDyk14MGAGUBxOqA4JZLrderpAwAHOR0y1j+dpgAAAABJRU5ErkJggg=="
        }
        
        # 如果工具名称在字典中，返回对应的图标
        if tool_name in icon_data:
            pixmap = QPixmap()
            pixmap.loadFromData(base64.b64decode(icon_data[tool_name]))
            return QIcon(pixmap)
        
        # 如果找不到图标，返回一个空图标
        return QIcon()
    
    def create_mode_icon(self, mode):
        """创建填充模式图标"""
        # 创建一个20x20的图标
        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if mode == "outline":
            # 只有边框 - 空心矩形
            painter.setPen(QPen(Qt.black, 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(2, 2, 16, 16)
        elif mode == "filled":
            # 边框+填充 - 实心矩形带边框
            painter.setPen(QPen(Qt.black, 2))
            painter.setBrush(QBrush(QColor(128, 128, 128)))
            painter.drawRect(2, 2, 16, 16)
        elif mode == "fill_only":
            # 只有填充 - 实心矩形无边框
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(128, 128, 128)))
            painter.drawRect(2, 2, 16, 16)
        
        painter.end()
        return QIcon(pixmap)
    
    def set_fill_mode(self, mode, button):
        """设置填充模式"""
        # 取消其他按钮的选中状态
        for btn in self.mode_buttons:
            if btn != button:
                btn.setChecked(False)
        
        # 确保当前按钮保持选中状态
        button.setChecked(True)
        
        # 设置画布的填充模式
        self.canvas.shape_fill_mode = mode
        
        # 对于多边形工具，同步设置多边形填充模式
        if hasattr(self.canvas, 'polygon_fill_mode'):
            self.canvas.polygon_fill_mode = mode
    
    def create_color_palette_and_brush(self, parent_layout):
        """创建颜色选择器和笔刷设置"""
        color_widget = QWidget()
        self.color_palette_widget = color_widget  # 保存引用
        color_widget.setFixedHeight(110)  # 增加高度以适应两排颜色
        color_widget.setStyleSheet("background-color: #D4D0C8;")
        
        color_layout = QHBoxLayout(color_widget)
        color_layout.setContentsMargins(10, 5, 10, 5)
        
        # ===== 左侧颜色显示组件 =====
        color_display_container = QWidget()
        color_display_container.setFixedWidth(70)
        color_display_container_layout = QVBoxLayout(color_display_container)
        color_display_container_layout.setContentsMargins(0, 10, 0, 0)  # 增加上边距，向下移动
        
        self.color_display_widget = ColorDisplayWidget()
        color_display_container_layout.addWidget(self.color_display_widget)
        color_display_container_layout.addStretch()
        
        color_layout.addWidget(color_display_container)
        
        # 添加一些间距
        spacing_widget = QWidget()
        spacing_widget.setFixedWidth(10)
        color_layout.addWidget(spacing_widget)
        
        # ===== 中间颜色网格区域 =====
        colors_container = QWidget()
        colors_container.setFixedWidth(170)
        colors_layout = QVBoxLayout(colors_container)
        colors_layout.setContentsMargins(0, 10, 0, 0)  # 增加上边距，向下移动
        colors_layout.setSpacing(2)
        
        # 第一排颜色（8个）
        colors_grid1 = QGridLayout()
        colors_grid1.setSpacing(2)
        colors_grid1.setContentsMargins(0, 0, 0, 0)
        
        # 调色板颜色（按图片中的顺序）
        color_palette_row1 = [
            "#000000", "#808080", "#800000", "#FF0000", 
            "#800080", "#FF00FF", "#008000", "#00FF00"
        ]
        
        color_palette_row2 = [
            "#808000", "#FFFF00", "#000080", "#0000FF",
            "#008080", "#00FFFF", "#C0C0C0", "#FFFFFF"
        ]
        
        # 创建颜色按钮列表
        self.color_buttons = []
        
        # 第一排颜色按钮
        for i, color in enumerate(color_palette_row1):
            btn = self.create_color_button(color, i)
            colors_grid1.addWidget(btn, 0, i)
        
        # 第二排颜色（8个）
        colors_grid2 = QGridLayout()
        colors_grid2.setSpacing(2)
        colors_grid2.setContentsMargins(0, 0, 0, 0)
        
        for i, color in enumerate(color_palette_row2):
            btn = self.create_color_button(color, i + 8)
            colors_grid2.addWidget(btn, 0, i)
        
        colors_layout.addLayout(colors_grid1)
        colors_layout.addLayout(colors_grid2)
        colors_layout.addStretch()
        
        color_layout.addWidget(colors_container)
        
        # ===== 右侧笔刷设置区域 =====
        brush_widget = QWidget()
        brush_widget.setFixedWidth(150)
        brush_layout = QVBoxLayout(brush_widget)
        brush_layout.setContentsMargins(40, 10, 0, 0)  # 增加上边距，向下移动
        brush_layout.setSpacing(5)
        
        # 线宽选择
        line_width_widget = QWidget()
        line_width_layout = QHBoxLayout(line_width_widget)
        line_width_layout.setContentsMargins(0, 0, 0, 0)
        
        line_width_label = QLabel("线宽:")
        line_width_label.setStyleSheet("font-size: 9px; color: black;")
        line_width_label.setFixedWidth(30)
        
        line_width_spin = QSpinBox()
        line_width_spin.setRange(1, 50)
        line_width_spin.setValue(2)
        line_width_spin.setFixedWidth(80)
        line_width_spin.valueChanged.connect(self.canvas.set_pen_width)
        
        line_width_layout.addWidget(line_width_label)
        line_width_layout.addWidget(line_width_spin)
        line_width_layout.addStretch()
        
        # 线型选择
        line_style_widget = QWidget()
        line_style_layout = QHBoxLayout(line_style_widget)
        line_style_layout.setContentsMargins(0, 0, 0, 0)
        
        line_style_label = QLabel("线型:")
        line_style_label.setStyleSheet("font-size: 9px; color: black;")
        line_style_label.setFixedWidth(30)
        
        line_style_combo = QComboBox()
        line_style_combo.addItems(["实线", "虚线", "点线", "点划线", "双点划线"])
        line_style_combo.setCurrentIndex(0)
        line_style_combo.setFixedWidth(80)
        line_style_combo.currentIndexChanged.connect(self.canvas.set_pen_style)
        
        line_style_layout.addWidget(line_style_label)
        line_style_layout.addWidget(line_style_combo)
        line_style_layout.addStretch()
        
        brush_layout.addWidget(line_width_widget)
        brush_layout.addWidget(line_style_widget)
        brush_layout.addStretch()
        
        color_layout.addWidget(brush_widget)
        color_layout.addStretch()
        
        parent_layout.addWidget(color_widget)
        return color_widget
    
    def create_color_button(self, color, index):
        """创建颜色按钮"""
        btn = QPushButton()
        btn.setFixedSize(20, 20)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: 1px solid black;
            }}
            QPushButton:hover {{
                border: 2px solid #404040;
            }}
            QPushButton:pressed, QPushButton:checked {{
                border: 3px solid #000000;
            }}
        """)
        btn.setCheckable(True)
        
        # 默认选中黑色
        if color == "#000000":
            btn.setChecked(True)
        
        # 左键点击设置前景色
        btn.clicked.connect(lambda checked, c=color: self.change_fg_color(c))
        
        # 右键点击设置背景色
        btn.setContextMenuPolicy(Qt.CustomContextMenu)
        btn.customContextMenuRequested.connect(
            lambda pos, c=color: self.set_background_color(c)
        )
        
        # 保存按钮引用
        self.color_buttons.append(btn)
        
        return btn
    
    def set_background_color(self, color_name):
        """设置背景颜色"""
        self.canvas.set_bg_color(QColor(color_name))
        self.color_display_widget.set_background_color(QColor(color_name))
    
    def select_tool(self, tool_name, button):
        """选择工具"""
        # 取消所有其他按钮的选中状态
        for btn in self.tool_buttons:
            if btn != button:
                btn.setChecked(False)
        
        # 如果点击已选中的按钮，保持选中状态
        if button.isChecked():
            self.canvas.set_tool(tool_name)
        else:
            # 如果取消选中，重新选中它（必须有一个工具被选中）
            button.setChecked(True)
        
        # 根据当前工具显示或隐藏填充模式选择器
        if hasattr(self, 'mode_label') and hasattr(self, 'mode_widget'):
            if tool_name in ["rectangle", "ellipse", "polygon", "rounded"]:
                self.mode_label.show()
                self.mode_widget.show()
            else:
                self.mode_label.hide()
                self.mode_widget.hide()
    
    def change_fg_color(self, color_name):
        """改变前景颜色"""
        self.canvas.set_pen_color(QColor(color_name))
        
        # 更新颜色显示组件的前景色
        self.color_display_widget.set_foreground_color(QColor(color_name))
        
        # 更新颜色按钮的选中状态
        for btn in self.color_buttons:
            if f"background-color: {color_name};" in btn.styleSheet():
                btn.setChecked(True)
            else:
                btn.setChecked(False)
    
    def show_image_properties(self):
        """显示图像属性对话框"""
        # 获取当前画布尺寸
        current_width = self.canvas.image.width()
        current_height = self.canvas.image.height()
        
        dialog = ImagePropertiesDialog(self, current_width, current_height)
        if dialog.exec_() == QDialog.Accepted:
            # 获取新的尺寸
            new_width, new_height = dialog.get_dimensions()
            is_color = dialog.is_color_mode()
            
            # 应用新尺寸到画布
            self.resize_canvas(new_width, new_height)
    
    def edit_colors(self):
        """编辑颜色 - 打开系统颜色编辑对话框"""
        # 获取当前前景色
        current_color = self.canvas.pen_color
        
        # 打开系统颜色对话框
        color = QColorDialog.getColor(current_color, self, "编辑颜色")
        
        # 如果用户选择了有效颜色，则更新前景色
        if color.isValid():
            self.change_fg_color(color.name())
    
    def resize_canvas(self, width, height):
        """调整画布大小"""
        # 创建新图像
        new_image = QPixmap(width, height)
        new_image.fill(Qt.white)
        
        # 将原始图像绘制到新画布上（保持内容）
        painter = QPainter(new_image)
        painter.drawPixmap(0, 0, self.canvas.image)
        painter.end()
        
        # 更新画布
        self.canvas.image = new_image
        self.canvas._apply_zoom()
    
    def show_stretch_skew_dialog(self):
        """显示拉伸和扭曲对话框"""
        dialog = StretchSkewDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            horizontal_stretch = dialog.horizontal_stretch_spin.value()
            vertical_stretch = dialog.vertical_stretch_spin.value()
            horizontal_skew = dialog.horizontal_skew_spin.value()
            vertical_skew = dialog.vertical_skew_spin.value()
            
            # 应用拉伸
            self.canvas.stretch_image(horizontal_stretch, vertical_stretch)
            
            # 应用扭曲
            if horizontal_skew != 0 or vertical_skew != 0:
                self.canvas.skew_image(horizontal_skew, vertical_skew)
    
    def show_flip_rotate_dialog(self):
        """显示翻转和旋转对话框"""
        dialog = FlipRotateDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            selection = dialog.get_selection()
            
            if selection == "horizontal":
                self.canvas.flip_image("horizontal")
            elif selection == "vertical":
                self.canvas.flip_image("vertical")
            elif selection == "rotate_90":
                self.canvas.rotate_image(90)
            elif selection == "rotate_180":
                self.canvas.rotate_image(180)
            elif selection == "rotate_270":
                self.canvas.rotate_image(270)

    def show_ai_setup_dialog(self):
        """显示AI设置对话框"""
        dialog = AISetupDialog(self, self.ai_settings)
        if dialog.exec_() == QDialog.Accepted:
            # 保存用户的设置
            self.ai_settings = dialog.get_settings()
            # 保存到配置文件
            self.save_ai_config(self.ai_settings)
            self.statusBar().showMessage("AI设置已更新并保存到配置文件")
    
    def show_ai_generate_dialog(self):
        """显示AI生成对话框"""
        dialog = AIGenerateDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # 获取生成的图像数据
            if hasattr(dialog, 'generated_images') and dialog.generated_images:
                # 将第一个图像应用到画布
                image_data = dialog.generated_images[0]
                self.apply_ai_image_to_canvas(image_data)
                self.statusBar().showMessage(f"AI图像生成完成，共生成 {len(dialog.generated_images)} 张图像")
            else:
                QMessageBox.warning(self, "提示", "未能获取生成的图像")
    
    def apply_ai_image_to_canvas(self, image_data):
        """将AI生成的图像应用到画布"""
        try:
            # 解码base64图像数据
            import base64
            from PyQt5.QtGui import QImage
            
            # 将base64数据转换为QImage
            image_bytes = base64.b64decode(image_data)
            image = QImage.fromData(image_bytes)
            
            if image.isNull():
                # 如果解码失败，创建默认图像
                pixmap = QPixmap(512, 512)
                pixmap.fill(Qt.white)
                painter = QPainter(pixmap)
                painter.setPen(QPen(Qt.black, 2))
                painter.drawText(200, 250, "AI Generated Image")
                painter.end()
            else:
                pixmap = QPixmap.fromImage(image)
            
            # 调整图像大小以适应画布
            canvas_size = self.canvas.size()
            scaled_pixmap = pixmap.scaled(canvas_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # 创建新图像以居中显示
            final_image = QPixmap(canvas_size)
            final_image.fill(Qt.white)
            
            painter = QPainter(final_image)
            # 计算居中位置
            x = (canvas_size.width() - scaled_pixmap.width()) // 2
            y = (canvas_size.height() - scaled_pixmap.height()) // 2
            painter.drawPixmap(x, y, scaled_pixmap)
            painter.end()
            
            # 应用到画布
            self.canvas.image = final_image
            self.canvas.update()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用AI图像失败: {str(e)}")
    
    def toggle_toolbox(self):
        """切换工具箱显示/隐藏"""
        if self.toolbox_action.isChecked():
            self.toolbox_widget.show()
        else:
            self.toolbox_widget.hide()
    
    def toggle_color_palette(self):
        """切换颜色盒显示/隐藏"""
        if self.color_palette_action.isChecked():
            self.color_palette_widget.show()
        else:
            self.color_palette_widget.hide()
    
    def toggle_status_bar(self):
        """切换状态栏显示/隐藏"""
        if self.status_bar_action.isChecked():
            self.status_bar.show()
        else:
            self.status_bar.hide()
    
    def toggle_text_toolbar(self):
        """切换文字工具栏显示/隐藏"""
        # 只有在文字工具时才允许切换，否则忽略点击
        if self.canvas.current_tool != "text":
            # 非文字工具状态下，强制保持未选中状态并返回
            self.text_toolbar_action.setChecked(False)
            return
            
        if self.text_toolbar_action.isChecked():
            # 显示文字工具栏
            if not self.canvas.text_tool_dialog:
                self.canvas.text_tool_dialog = TextToolDialog()
                # 连接对话框关闭信号，更新菜单状态
                self.canvas.text_tool_dialog.finished.connect(self.on_text_toolbar_closed)
            self.canvas.text_tool_dialog.show()
            # 确保菜单项为选中状态（带钩）
            self.text_toolbar_action.setChecked(True)
        else:
            # 隐藏文字工具栏
            if self.canvas.text_tool_dialog:
                self.canvas.text_tool_dialog.hide()
    
    def on_text_toolbar_closed(self):
        """文字工具栏关闭时的处理"""
        # 更新菜单状态为未选中
        self.text_toolbar_action.setChecked(False)
        # 清理对话框引用
        self.canvas.text_tool_dialog = None
    
    def sync_text_toolbar_menu_state(self):
        """同步文字工具栏菜单状态与对话框实际存在状态"""
        if self.canvas.current_tool == "text":
            # 文字工具时，菜单项可用
            self.text_toolbar_action.setEnabled(True)
            # 同步对话框存在状态与菜单选中状态
            dialog_exists = (self.canvas.text_tool_dialog is not None and
                           self.canvas.text_tool_dialog.isVisible())
            menu_checked = self.text_toolbar_action.isChecked()
            
            # 如果对话框存在状态与菜单选中状态不一致，进行同步
            if dialog_exists != menu_checked:
                self.text_toolbar_action.setChecked(dialog_exists)
        else:
            # 非文字工具时，菜单项灰色不可用且不带对勾
            self.text_toolbar_action.setEnabled(False)
            self.text_toolbar_action.setChecked(False)


    def new_file(self):
        """新建文件"""
        # 检查是否有未保存的更改
        if self.canvas.is_content_modified():
            reply = QMessageBox.question(
                self, "确认新建",
                "当前有未保存的更改，是否保存？",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Save:
                self.save_file()
            elif reply == QMessageBox.Cancel:
                return
        
        # 创建新的空白画布
        self.canvas.image = QPixmap(720, 520)  # 默认尺寸
        self.canvas.image.fill(Qt.white)
        self.canvas.reset_zoom()  # 重置缩放到100%
        
        # 重置文件路径和画布状态
        self.current_file_path = None
        self.canvas.reset_content_modified_flag()
        self.statusBar().showMessage("新建文件")
        
        # 重置窗口标题为"未命名 - 画图"
        self.setWindowTitle("未命名 - 画图")
    
    def open_file(self):
        """打开文件"""
        # 检查是否有未保存的更改
        if self.canvas.is_content_modified():
            reply = QMessageBox.question(
                self, "确认打开",
                "当前有未保存的更改，是否保存？",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Save:
                self.save_file()
            elif reply == QMessageBox.Cancel:
                return
        
        # 打开文件对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开图像", "",
            "图像文件 (*.bmp *.jpg *.jpeg *.png *.gif *.tiff *.ico);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                # 加载图像
                image = QPixmap(file_path)
                if image.isNull():
                    QMessageBox.warning(self, "错误", "无法打开所选文件。")
                    return
                
                # 应用到画布
                self.canvas.image = image
                self.canvas.reset_zoom()  # 重置缩放到100%
                
                # 更新文件路径和画布状态
                self.current_file_path = file_path
                self.canvas.reset_content_modified_flag()
                self.statusBar().showMessage(f"已打开: {file_path}")
                
                # 更新窗口标题为文件名
                file_name = os.path.basename(file_path)
                self.setWindowTitle(f"{file_name} - 画图")
                
            except Exception as e:
                QMessageBox.warning(self, "错误", f"打开文件失败: {str(e)}")
    
    def save_file(self):
        """保存文件"""
        if hasattr(self, 'current_file_path') and self.current_file_path:
            # 如果已有文件路径，直接保存
            try:
                self.canvas.image.save(self.current_file_path)
                self.canvas.reset_content_modified_flag()
                self.statusBar().showMessage(f"已保存: {self.current_file_path}")
                
                # 更新窗口标题为文件名
                file_name = os.path.basename(self.current_file_path)
                self.setWindowTitle(f"{file_name} - 画图")
                
                return True
            except Exception as e:
                QMessageBox.warning(self, "错误", f"保存文件失败: {str(e)}")
                return False
        else:
            # 否则执行"另存为"
            return self.save_as_file()
    
    def save_as_file(self):
        """另存为文件"""
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "另存为", "",
            "PNG 图像 (*.png);;JPEG 图像 (*.jpg *.jpeg);;BMP 图像 (*.bmp);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                # 确保文件有正确的扩展名
                if not file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    # 根据选择的过滤器添加扩展名
                    if "PNG" in selected_filter:
                        file_path += ".png"
                    elif "JPEG" in selected_filter:
                        file_path += ".jpg"
                    elif "BMP" in selected_filter:
                        file_path += ".bmp"
                
                # 保存图像
                if self.canvas.image.save(file_path):
                    self.current_file_path = file_path
                    self.canvas.reset_content_modified_flag()
                    self.statusBar().showMessage(f"已保存: {file_path}")
                    
                    # 更新窗口标题为文件名
                    file_name = os.path.basename(file_path)
                    self.setWindowTitle(f"{file_name} - 画图")
                    
                    return True
                else:
                    QMessageBox.warning(self, "错误", "保存文件失败。")
                    return False
                    
            except Exception as e:
                QMessageBox.warning(self, "错误", f"保存文件失败: {str(e)}")
                return False
        
        return False

    def invert_colors(self):
        """反色图像 - 调用画布的invert_colors方法"""
        self.canvas.invert_colors()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MSPaintWindow()
    window.show()
    sys.exit(app.exec_())