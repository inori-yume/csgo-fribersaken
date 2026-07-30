# 🎯 CS2 Friberg 猜选手辅助工具

基于[csgo弗一把](https://github.com/shnlfriberg/csgofriberg)项目，自动监控 Friberg 猜选手游戏，智能筛选候选选手的辅助工具。

## ✨ 功能特点

- 🤖 自动监控游戏页面表格数据
- 🎯 智能筛选：支持正确/接近/错误三种反馈
- 🌍 赛区映射：自动将国籍映射到对应赛区
- 🖥️ 图形界面：Tkinter 分页显示候选列表
- 📊 累积筛选：综合所有历史猜测记录

## 🚀 快速开始

### 安装依赖
```bash
pip install selenium webdriver-manager
```

### 准备数据
确保 `players.json` 存在于程序目录，格式如下：
```json
[
  {
    "nickname": "device",
    "team": "Astralis",
    "nationality": "丹麦",
    "age": 27,
    "role": "AWPer",
    "major_championships": 4,
    "major_appearances": 10,
    "is_active": true,
    "is_enabled": true
  }
]
```

### 运行
```bash
python friberg.py
```

### 使用步骤
1. 程序自动打开 Chrome 浏览器
2. 登录并进入游戏对局
3. 控制台按 Enter 开始监控
4. 候选窗口自动弹出并更新

## 🎮 工作原理

### 反馈类型
- **正确 (correct)**：精确匹配该字段
- **接近 (close)**：赛区匹配或数值范围筛选
- **错误 (wrong)**：排除该值或赛区

### 筛选逻辑
- **正确**：精确匹配字段值
- **接近/错误+箭头**：
  - 国籍 → 映射到赛区
  - 数值 → 根据箭头方向（↑更大/↓更小）筛选
- **错误**：排除该值或对应赛区

## 📁 文件结构
```
friberg/
├── friberg.py      # 主程序
├── players.json    # 选手数据
└── README.md       # 说明文档
```

## 🔧 自定义配置

### 修改监控间隔
```python
monitor.monitor_loop(interval=1.0)  # 改为每秒检测
```

### 修改分页大小
```python
self.page_size = 100  # 每页显示100条
```

### 更新国籍映射
```python
NATIONALITY_TO_REGION = {
    "中国": "亚太",
    "丹麦": "欧洲",
    # 添加新映射...
}
```

## ⚠️ 注意事项

1. 需要 Chrome 浏览器
2. 确保网络稳定
3. 游戏更新可能导致页面结构变化
4. `players.json` 数据需完整准确

## 🐛 常见问题

**Q: Chrome 无法启动？**
```bash
pip install webdriver-manager --upgrade
```

**Q: 候选列表不更新？**
- 确认已进入游戏对局
- 检查控制台错误信息
- 点击"刷新"按钮

**Q: 显示无候选选手？**
- 点击"新的一轮"重置
- 检查猜测是否正确

## 📄 许可证
本项目基于AGPL-3.0开源。  

[csgo弗一把](https://github.com/shnlfriberg/csgofriberg)原项目作者：[B站-怂皇的一天](https://space.bilibili.com/290893104)  

仅供本地娱乐参考，请勿用于线上作弊使用。  
联系侵删。

---

**祝游戏愉快！** 🎮