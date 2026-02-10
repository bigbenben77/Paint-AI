import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QGridLayout, QPushButton, QLabel,
                             QMenuBar, QMenu, QAction, QStatusBar, QScrollArea,
                             QComboBox, QSpinBox, QDoubleSpinBox, QFrame, QDialog, QDialogButtonBox,
                             QGroupBox, QRadioButton, QLineEdit, QFormLayout,
                             QMessageBox, QFileDialog, QFontDialog,
                             QTabWidget, QCheckBox, QSlider, QTextEdit, QProgressBar)  # 添加缺失的类
from PyQt5.QtCore import Qt, QPoint, QRect, QTimer, QSize, QThread, pyqtSignal, QMimeData
from PyQt5.QtGui import QPainter, QPen, QColor, QPixmap, QIcon, QFont, QTransform, QBrush, QImage
from PyQt5.QtGui import QClipboard, QPainterPath  # 添加剪贴板支持和绘图路径
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


class AIGenerateDialog(QDialog):
    """AI生成提示词对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI图像生成")
        self.setFixedSize(500, 400)
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
        self.prompt_textedit.setMaximumHeight(100)
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
                    padding: 3px;
                    text-align: left;
                    font-size: 11px;
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


class TextToolDialog(QDialog):
    """文字工具对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("文字工具栏")
        self.setFixedSize(250, 80)
        
        layout = QVBoxLayout(self)
        
        # 字体选择区域
        font_widget = QWidget()
        font_layout = QHBoxLayout(font_widget)
        
        self.font_combo = QComboBox()
        self.font_combo.addItems(["Fixesys", "Arial", "Times New Roman", "Courier New"])
        self.font_combo.setEditable(True)
        self.font_combo.setCurrentText("Fixesys")
        
        self.size_combo = QComboBox()
        self.size_combo.addItems(["8", "9", "10", "11", "12", "14", "16", "18", "20", "22", "24"])
        self.size_combo.setEditable(True)
        self.size_combo.setCurrentText("12")
        
        font_layout.addWidget(self.font_combo)
        font_layout.addWidget(self.size_combo)
        
        layout.addWidget(font_widget)
        
        # 按钮区域
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        
        self.bold_btn = QPushButton("B")
        self.bold_btn.setCheckable(True)
        self.bold_btn.setFixedSize(30, 30)
        
        self.italic_btn = QPushButton("I")
        self.italic_btn.setCheckable(True)
        self.italic_btn.setFixedSize(30, 30)
        
        self.underline_btn = QPushButton("U")
        self.underline_btn.setCheckable(True)
        self.underline_btn.setFixedSize(30, 30)
        
        button_layout.addWidget(self.bold_btn)
        button_layout.addWidget(self.italic_btn)
        button_layout.addWidget(self.underline_btn)
        button_layout.addStretch()
        
        layout.addWidget(button_widget)
        
        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background-color: #ECE9D8;
            }
            QPushButton {
                background-color: #D4D0C8;
                border: 1px solid #808080;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #E8E5D8;
            }
            QPushButton:pressed, QPushButton:checked {
                background-color: #C0C0C0;
                border: 2px inset #404040;
            }
        """)
    
    def get_font(self):
        """获取选中的字体"""
        font = QFont(self.font_combo.currentText(), int(self.size_combo.currentText()))
        font.setBold(self.bold_btn.isChecked())
        font.setItalic(self.italic_btn.isChecked())
        font.setUnderline(self.underline_btn.isChecked())
        return font


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
        
        # 画布调整大小相关
        self.resizing_mode = None  # "right", "bottom", "corner"
        self.resizing_start_pos = QPoint()
        self.original_size = QSize()
        self.resize_handle_size = 8  # 控制点大小
        self.original_image = None  # 原始图像副本，用于调整大小
        
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
            # 调整画布大小以匹配新图像
            self.setFixedSize(self.image.width(), self.image.height())
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
                    self.resizing_mode = "right"
                    self.resizing_start_pos = pos
                    self.original_size = self.image.size()
                    self.original_image = self.image.copy()
                    return
                elif bottom_rect.contains(pos):
                    self.resizing_mode = "bottom"
                    self.resizing_start_pos = pos
                    self.original_size = self.image.size()
                    self.original_image = self.image.copy()
                    return
                elif corner_rect.contains(pos):
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
            
            # 如果没有点击控制点和选区，则进行正常的绘图操作
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
                self.is_text_mode = True
                self.text_start_point = event.pos()
                self.text_content = ""
                # 根据鼠标按钮设置文字颜色
                self.pen_color = draw_color
                # 显示文字工具栏
                if not self.text_tool_dialog:
                    self.text_tool_dialog = TextToolDialog()
                self.text_tool_dialog.show()
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
            # 调整画布组件尺寸以匹配新图像大小
            self.setFixedSize(new_width, new_height)
            self.update()
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
            self.is_text_mode = False
    
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
        self.current_tool = tool
    
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
            # 直线
            painter.drawLine(start, end)
            
        elif self.current_tool == "rectangle":
            # 矩形
            rect = QRect(start, end).normalized()
            painter.drawRect(rect)
            
        elif self.current_tool == "ellipse":
            # 椭圆
            rect = QRect(start, end).normalized()
            painter.drawEllipse(rect)
            
        elif self.current_tool == "rounded":
            # 圆角矩形
            rect = QRect(start, end).normalized()
            painter.drawRoundedRect(rect, 20, 20)
    
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
            # 更新画布组件尺寸以匹配新图像大小
            self.setFixedSize(new_image.width(), new_image.height())
        
        self.update()
        self.mark_content_modified()
    
    def stretch_image(self, horizontal_percent, vertical_percent):
        """拉伸图像或选区"""
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


class MSPaintWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def load_ai_config(self):
        """从paint.ini配置文件加载AI设置，支持多模型配置"""
        config_file = 'paint.ini'
        
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
        config_file = 'paint.ini'
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
        config_file = 'paint.ini'
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
        self.create_toolbox(main_layout)
        
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
        self.create_color_palette_and_brush(middle_layout)
        
        # 状态栏
        status_bar = QStatusBar()
        status_bar.showMessage('按住 Shift 键并拖动"帮助"来查找主题。单击"帮助主题"。')
        status_bar.setStyleSheet("background-color: #D4D0C8; color: black;")
        middle_layout.addWidget(status_bar)
        
        main_layout.addWidget(middle_widget, stretch=1)
        
        # 设置窗口关闭事件处理
        self.setAttribute(Qt.WA_DeleteOnClose)
    
    def closeEvent(self, event):
        """窗口关闭事件处理"""
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
        file_menu.addAction("新建")
        file_menu.addAction("打开")
        file_menu.addAction("保存")
        file_menu.addAction("另存为")
        file_menu.addSeparator()
        self.ai_generate_action = file_menu.addAction("AI生成")
        self.ai_generate_action.triggered.connect(self.show_ai_generate_dialog)
        self.ai_setup_action = file_menu.addAction("AI设置")
        self.ai_setup_action.triggered.connect(self.show_ai_setup_dialog)
        file_menu.addSeparator()
        file_menu.addAction("打印")
        file_menu.addAction("预览")
        file_menu.addSeparator()
        file_menu.addAction("最近用文件")
        file_menu.addSeparator()
        exit_action = file_menu.addAction("退出")
        exit_action.triggered.connect(self.close)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑(&E)")
        edit_menu.addAction("撤销")
        edit_menu.addAction("重做")
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
        edit_menu.addAction("全选")
        edit_menu.addAction("清空选区")
        clear_action = edit_menu.addAction("清空画布")
        clear_action.triggered.connect(self.canvas.clear_canvas)
        
        # 查看菜单
        view_menu = menubar.addMenu("查看(&V)")
        view_menu.addAction("工具箱")
        view_menu.addAction("颜色盒")
        view_menu.addAction("状态栏")
        view_menu.addAction("文字工具栏")


        
        # 图像菜单
        image_menu = menubar.addMenu("图像(&I)")
        
        # 翻转/旋转菜单项
        flip_rotate_action = image_menu.addAction("翻转/旋转")
        flip_rotate_action.triggered.connect(self.show_flip_rotate_dialog)
        
        # 拉伸/扭曲菜单项
        stretch_skew_action = image_menu.addAction("拉伸/扭曲")
        stretch_skew_action.triggered.connect(self.show_stretch_skew_dialog)
        
        image_menu.addAction("反色")

        # 图像属性菜单项
        properties_action = image_menu.addAction("属性")
        properties_action.triggered.connect(self.show_image_properties)
        
        # 颜色菜单
        color_menu = menubar.addMenu("颜色(&C)")
        color_menu.addAction("编辑颜色")
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        help_menu.addAction("帮助主题")
        help_menu.addAction("关于画图")
        
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
        toolbox_layout.addStretch()
        
        main_layout.addWidget(toolbox)
    
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
    
    def create_color_palette_and_brush(self, parent_layout):
        """创建颜色选择器和笔刷设置"""
        color_widget = QWidget()
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
        line_width_spin.setFixedWidth(50)
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
        self.canvas.setFixedSize(width, height)
        self.canvas.update()
    
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MSPaintWindow()
    window.show()
    sys.exit(app.exec_())