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
    """关于Paint-AI - 捐赠对话框"""
    WECHAT_QR_BASE64 = """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SL2QeMouNwVTbt4HJ4iS5UCrmNNE2THXElaanamVur1+Iq64C0wXtl1+qL0Syk45Z19+68uGnCIJE48wk6VljCFCWo/JPhKl1B133FGtVh944IEs9s0wM7/zne+sVCo60/knpbzoootMESwLzRNC3HvvvUEQmNxr+l4opffdd59hsksnEedyuXvuuSdFn6Rx9KOPPvqBD3wgq1e+79u2fffdd5uZh+k5zTSJu+++O4slYIx1u9377rvPTLTItqPddNNN9957b0owdWYdu+666858wK+jrDVjBwAGHbpr166PfOQjacFLa23oiaamplzXfcHGTkr5gQ984OMf/7i5SrperVbvvvtuM0oRMrbmxhtvvOGGG9LPGrhft9vdtGlTCnFI7aP5RZ01QW402xD2mcpGum6KwgZs/PwKrQGUCWMZ41IxRK45Hd08XqnlkKGTI5qCQtSoOQGK2gZSKLgAiiByJBaipIgokYDrOqVKmS+1r73xxtJVWxvT0/VmyMq50thwbXiIAKImEiglQjMQKirUSjteWt14Ubu+vLC8vJy0tPKp1Imbt72i4+Vtq2CHKmk2Wgst+ZVvPzK13PHKwz7YSdztagd0zGPgyBVhi0uL9ebyxWMvOdpaLG8bWSLSKpQ79QbN5wuW50Wgl9olr9jtdAya2gw4BABySsf07bff7vv+F7/4RbPrpO/Ltu077rhjy5YtkEkHm2du+CayD1lK+R//8R9HjhzBk0dM/Nmf/dlf//Vfm204TbYGQfChD30oNXa6N8v8scce27VrV1a1TC3++PHjhUIhLYYYXfrbv/3b++67z7x0s27K7vfcc08+nzfGOj3/tddee91116WpxjPr2JosVqw1Y2fS84ZjMjv311T6DbATT56C+IueXymVzlHPVnLNkOM+TdKZ/moDAXFdt9Pp6JM5AtKSwmry1un30qcMGEup9AzU7vSfRzNcDChlCEgpHx4e3e83LA+KZZYoYFxrIiUIpSUBSgih1LIt3ajPTxaGXU651poRSYEo7Xj25i1bdj11sN5qX//SHUvV2lzDJ6VcV8uAWwyolhhL5BJcQROFiSIR0ayUqxVq5YlYB0p1VZhEQkqFmEjZimm725mdb/9w5xNTCw3Jc9SrWIVB1/MSuRJYELRDFSUMEBUfr5R5u1OWYmXvUVbKCZFcMDbSWunmCwVHSL8dYCyk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"""
    ALIPAY_QR_BASE64 = """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yNmB/xw/fnzonC0tLfAEwdiB+2b06NFtbW39BxAy2Rhj69evFz0oYBXuJIupFIRmraGhQR4zGkun0+nOzs7+R1X4ZtYARD8cx1m/fr38QQJNwCcwGL7DSeBCbW1tRbmqMm7HlpYWpCeXiU5kMhld1yORyKhRo2RLqrm5GdyHpQaXelBs3LhR7DagnFtYo/iadnd3izV+0f05511dXbVVptgVUXc+OwUFhfqEIjsFBYW6gCI7BQWFusCI9dlB/CW8xSIAj/x8eHzxT4iuyv4dSGFzuRyUqGI7/lPsbNt2c3NzLperxDcEHQN8/JCMRaPRytW/CMXiJHAMsYoLcKK7tijHKOQj8tjgfERSV4VDAkR31JAPkRakvEJUjJ9AHrMQ35XxP0LtrGmakGrj98KvAEmafE48UsjTED7G7w7vFWoRl7oc5zybzSJmxRgTISzofso3iED8VzThLroPJmT/Cp1w1ZFCQb1SlygK5Gwg16WUVg4BXES35CkHYRBGWw/qkxFLdpqmvf7666+99homkHDTTpw48YILLgBnQTpn2/aTTz7Z1dUlH/7uu+/edtttsVhM9jfjbEI4yjnP5/N/+tOfXnrppQHH09vbu2DBglQqBa4xTTMej+++++6V3Msee+xx7rnnommLoLx33nln+fLlAx47adKkE044AS8wKbi9X3zxxWXLlol9dF03TfP0009vbW2tZDwyoLk98cQTJ0+eLL/knZ2djz76qOd50GFgzG+//fZtt90WOrapqenSSy8txSOUUii3dV2/5557RGkWnHDp0qWhD4bjOA8++GBbW1symYTWjBCydevWXC43YPErxtgZZ5yx3377ua6LLBfOeUtLS0tLy4CKaE3Tjj322DFjxvDSdeUcx4lEIuPGjQsxC2Nszpw5l1xySSQSqTb7glJ65JFH9s9+kQEVTkNDw5lnnhmq/HrggQeie3pVF91FMWLJjhDyv//7vz/5yU9k0ROl9MEHHzzxxBOh1dR1PZfLrVmz5vnnnw+R3dKlS99++21SSCGQISwRXde7u7tvu+22Siysyy+/fNGiRQgRItpbuSBjzpw5mJSwU2B1nnXWWf/1X/814LHHHnvsl7/8ZdhEGLZt24899tjdd98t39GYMWP23XdfvNUVjgoIgiAajZ511lmhl/zdd9996aWXNmzYAG7CyN9888033nhDvq6u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"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于Paint-AI - 捐赠")
        self.setFixedSize(800, 800)
        self.setModal(True)
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("支持Paint-AI作者 - 捐赠支持1元")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 描述
        description_label = QLabel(
            "感谢您使用Paint-AI！\n\n"
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
            # 创建自定义消息框
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("错误")
            msg_box.setText("正确生成图片请在设置对话框设置正确的参数")
            
            # 添加按钮
            ok_button = msg_box.addButton("确定", QMessageBox.AcceptRole)
            cancel_button = msg_box.addButton("取消", QMessageBox.RejectRole)
            
            # 显示消息框
            result = msg_box.exec_()
            
            # 根据用户选择处理
            if msg_box.clickedButton() == ok_button:
                # 打开设置对话框
                self.open_ai_setup_dialog()
            # 如果点击取消，则直接返回画图应用界面（无需额外处理）
    
    def on_generation_error(self, error_msg):
        """生成错误"""
        self.progress_bar.setVisible(False)
        self.generate_button.setEnabled(True)
        
        # 创建自定义消息框
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("错误")
        msg_box.setText("正确生成图片请在设置对话框设置正确的参数")
        
        # 添加按钮
        ok_button = msg_box.addButton("确定", QMessageBox.AcceptRole)
        cancel_button = msg_box.addButton("取消", QMessageBox.RejectRole)
        
        # 显示消息框
        result = msg_box.exec_()
        
        # 根据用户选择处理
        if msg_box.clickedButton() == ok_button:
            # 打开设置对话框
            self.open_ai_setup_dialog()
        # 如果点击取消，则直接返回画图应用界面（无需额外处理）
    
    def open_ai_setup_dialog(self):
        """打开AI设置对话框"""
        # 获取父窗口（主窗口）
        parent_window = self.parent_window
        if parent_window and hasattr(parent_window, 'show_ai_setup_dialog'):
            parent_window.show_ai_setup_dialog()


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
        """完成多边形绘制（对标画图）"""
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
        self.save_state()  # 保存状态用于撤销
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
        
        # 绘制多边形预览（对标画图）
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
            # 创建自定义按钮的对话框
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("保存更改")
            msg_box.setText("画布内容已更改。\n\n是否保存更改？")
            msg_box.setIcon(QMessageBox.Question)
            
            # 添加中文按钮
            save_button = msg_box.addButton("保存", QMessageBox.AcceptRole)
            discard_button = msg_box.addButton("弃存", QMessageBox.DestructiveRole)
            cancel_button = msg_box.addButton("取消", QMessageBox.RejectRole)
            
            # 设置默认按钮
            msg_box.setDefaultButton(save_button)
            
            # 显示对话框
            msg_box.exec_()
            
            # 获取点击的按钮
            clicked_button = msg_box.clickedButton()
            
            if clicked_button == save_button:
                # 尝试保存文件
                if not self.save_current_file():
                    # 如果保存失败或被取消，阻止关闭
                    event.ignore()
                    return
            elif clicked_button == cancel_button:
                # 取消关闭
                event.ignore()
                return
            # 如果选择的是discard_button，则直接关闭
        
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
        self.about_action = help_menu.addAction("关于Paint-AI")
        self.about_action.triggered.connect(self.about_paint)
        
    def about_paint(self):
        """关于Paint-AI - 显示捐赠信息对话框"""
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
            # 创建自定义按钮的对话框
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("确认新建")
            msg_box.setText("当前有未保存的更改，是否保存？")
            msg_box.setIcon(QMessageBox.Question)
            
            # 添加中文按钮
            save_button = msg_box.addButton("保存", QMessageBox.AcceptRole)
            discard_button = msg_box.addButton("弃存", QMessageBox.DestructiveRole)
            cancel_button = msg_box.addButton("取消", QMessageBox.RejectRole)
            
            # 设置默认按钮
            msg_box.setDefaultButton(save_button)
            
            # 显示对话框
            msg_box.exec_()
            
            # 获取点击的按钮
            clicked_button = msg_box.clickedButton()
            
            if clicked_button == save_button:
                self.save_file()
            elif clicked_button == cancel_button:
                return
            
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
            # 创建自定义按钮的对话框
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("确认打开")
            msg_box.setText("当前有未保存的更改，是否保存？")
            msg_box.setIcon(QMessageBox.Question)
            
            # 添加中文按钮
            save_button = msg_box.addButton("保存", QMessageBox.AcceptRole)
            discard_button = msg_box.addButton("弃存", QMessageBox.DestructiveRole)
            cancel_button = msg_box.addButton("取消", QMessageBox.RejectRole)
            
            # 设置默认按钮
            msg_box.setDefaultButton(save_button)
            
            # 显示对话框
            msg_box.exec_()
            
            # 获取点击的按钮
            clicked_button = msg_box.clickedButton()
            
            if clicked_button == save_button:
                self.save_file()
            elif clicked_button == cancel_button:
                return
            
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