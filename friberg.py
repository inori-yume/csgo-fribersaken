# friberg.py
import time
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
from typing import List, Dict, Optional
import tkinter as tk
from tkinter import ttk
import threading
import traceback

# ========== 国籍→赛区映射（由 analyze_players.py 生成） ==========
NATIONALITY_TO_REGION = {
    "中国": "亚太",
    "丹麦": "欧洲",
    "乌克兰": "欧洲",
    "乌兹别克斯坦": "独联体",
    "乌拉圭": "南美洲",
    "以色列": "非洲与以色列",
    "俄罗斯": "独联体",
    "保加利亚": "欧洲",
    "加拿大": "北美洲",
    "匈牙利": "欧洲",
    "北马其顿": "欧洲",
    "南非": "非洲与以色列",
    "印度": "亚太",
    "印度尼西亚": "亚太",
    "危地马拉": "北美洲",
    "哈萨克斯坦": "独联体",
    "土耳其": "亚太",
    "塞尔维亚": "欧洲",
    "塞尔维亚科索沃": "欧洲",
    "巴西": "南美洲",
    "德国": "欧洲",
    "拉脱维亚": "欧洲",
    "挪威": "欧洲",
    "捷克": "欧洲",
    "斯洛伐克": "欧洲",
    "新西兰": "大洋洲",
    "智利": "南美洲",
    "比利时": "欧洲",
    "法国": "欧洲",
    "波兰": "欧洲",
    "波黑": "欧洲",
    "澳大利亚": "大洋洲",
    "爱沙尼亚": "欧洲",
    "瑞典": "欧洲",
    "瑞士": "欧洲",
    "白俄罗斯": "独联体",
    "立陶宛": "欧洲",
    "约旦": "亚太",
    "罗马尼亚": "欧洲",
    "美国": "北美洲",
    "芬兰": "欧洲",
    "英国": "欧洲",
    "荷兰": "欧洲",
    "葡萄牙": "欧洲",
    "蒙古": "亚太",
    "西班牙": "欧洲",
    "阿塞拜疆": "独联体",
    "阿根廷": "南美洲",
    "马来西亚": "亚太",
    "黑山": "欧洲",
}

# ---------- 选手数据加载 ----------
class PlayerDB:
    def __init__(self, json_file="players.json"):
        self.players = []
        self.nationality_to_region = NATIONALITY_TO_REGION
        self.load_players(json_file)
    
    def load_players(self, json_file):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    raw = data
                elif isinstance(data, dict) and 'players' in data:
                    raw = data['players']
                else:
                    raw = []
                self.players = [p for p in raw if p.get('is_enabled', True)]
                print(f"✅ 加载了 {len(self.players)} 名选手")
        except Exception as e:
            print(f"❌ 加载选手数据失败: {e}")
            self.players = []

    def get_region_by_nationality(self, nationality: str) -> str:
        """根据国籍获取赛区"""
        return self.nationality_to_region.get(nationality, "未知")

    def filter_candidates(self, guess_data: dict, reset: bool = False) -> List[dict]:
        """根据猜测反馈筛选候选选手"""
        if reset:
            print(f"\n🔄 新的一轮！重置所有筛选条件")
            return self.players.copy()
        
        candidates = self.players.copy()
        filters = []
        
        # ========== 字段映射（中文 → 数据库值） ==========
        ROLE_MAPPING = {
            '步枪手': 'Rifler',
            '狙击手': 'AWPer',
            '教练': 'Coach',
            '指挥': 'IGL',
            '突破手': 'Entry',
            '支援': 'Support',
            '自由人': 'Lurker',
        }
        
        print(f"\n🔍 应用筛选条件...")
        
        for field in ['nickname', 'team', 'nationality', 'age', 'role', 
                      'major_championships', 'major_appearances', 'is_active']:
            
            field_value = guess_data.get(field)
            
            # 跳过空值
            if field_value is None or field_value == '':
                continue
            
            status = guess_data.get(f'{field}_status')
            direction = guess_data.get(f'{field}_direction')
            
            # ====== 字段值转换 ======
            mapped_value = field_value
            
            if field == 'role':
                # 角色：中文 → 英文
                mapped_value = ROLE_MAPPING.get(field_value, field_value)
                if mapped_value != field_value:
                    print(f"    🔄 角色映射: {field_value} → {mapped_value}")
            
            if field == 'is_active':
                # 状态：中文 → 布尔
                if field_value == '现役':
                    mapped_value = True
                elif field_value == '退役':
                    mapped_value = False
                else:
                    mapped_value = field_value
            
            # 使用映射后的值进行筛选
            if status == 'correct':
                # 完全正确：精确匹配
                if field == 'nickname':
                    filters.append(f"昵称 = {field_value}")
                    candidates = [p for p in candidates if p['nickname'].lower() == field_value.lower()]
                elif field == 'team':
                    filters.append(f"队伍 = {field_value}")
                    candidates = [p for p in candidates if p['team'] == mapped_value]
                elif field == 'nationality':
                    filters.append(f"国籍 = {field_value}")
                    candidates = [p for p in candidates if p['nationality'] == field_value]
                elif field == 'role':
                    filters.append(f"位置 = {field_value} → {mapped_value}")
                    candidates = [p for p in candidates if p['role'] == mapped_value]
                elif field == 'age':
                    filters.append(f"年龄 = {field_value}")
                    candidates = [p for p in candidates if p['age'] == field_value]
                elif field == 'major_championships':
                    filters.append(f"Major冠军 = {field_value}")
                    candidates = [p for p in candidates if p['major_championships'] == field_value]
                elif field == 'major_appearances':
                    filters.append(f"Major次数 = {field_value}")
                    candidates = [p for p in candidates if p['major_appearances'] == field_value]
                elif field == 'is_active':
                    filters.append(f"状态 = {field_value}")
                    candidates = [p for p in candidates if p['is_active'] == mapped_value]
            
            elif status == 'close':
                # 接近答案：根据箭头方向判断
                if field == 'nationality':
                    target_region = self.get_region_by_nationality(field_value)
                    if target_region and target_region != "未知":
                        filters.append(f"赛区 = {target_region} (国家:{field_value} 接近)")
                        candidates = [p for p in candidates if p.get('region', '') == target_region]
                    else:
                        filters.append(f"国籍接近 = {field_value}")
                        candidates = [p for p in candidates if p['nationality'] == field_value]
                elif field == 'age':
                    if direction == 'up':
                        filters.append(f"年龄 > {field_value} (目标更大 ↑)")
                        candidates = [p for p in candidates if p['age'] > field_value]
                    elif direction == 'down':
                        filters.append(f"年龄 < {field_value} (目标更小 ↓)")
                        candidates = [p for p in candidates if p['age'] < field_value]
                    else:
                        print(f"    ⚠️ 年龄无箭头，跳过筛选")
                elif field == 'major_championships':
                    if direction == 'up':
                        filters.append(f"Major冠军 > {field_value} (目标更大 ↑)")
                        candidates = [p for p in candidates if p['major_championships'] > field_value]
                    elif direction == 'down':
                        filters.append(f"Major冠军 < {field_value} (目标更小 ↓)")
                        candidates = [p for p in candidates if p['major_championships'] < field_value]
                    else:
                        print(f"    ⚠️ Major冠军无箭头，跳过筛选")
                elif field == 'major_appearances':
                    if direction == 'up':
                        filters.append(f"Major次数 > {field_value} (目标更大 ↑)")
                        candidates = [p for p in candidates if p['major_appearances'] > field_value]
                    elif direction == 'down':
                        filters.append(f"Major次数 < {field_value} (目标更小 ↓)")
                        candidates = [p for p in candidates if p['major_appearances'] < field_value]
                    else:
                        print(f"    ⚠️ Major次数无箭头，跳过筛选")
                elif field == 'is_active':
                    filters.append(f"状态 = {field_value}")
                    candidates = [p for p in candidates if p['is_active'] == mapped_value]
            
            elif status == 'wrong' and direction:
                # 错误且有方向指示
                if field == 'age':
                    if direction == 'up':
                        filters.append(f"年龄 > {field_value} (数值偏小 ↑)")
                        candidates = [p for p in candidates if p['age'] > field_value]
                    elif direction == 'down':
                        filters.append(f"年龄 < {field_value} (数值偏大 ↓)")
                        candidates = [p for p in candidates if p['age'] < field_value]
                elif field == 'major_championships':
                    if direction == 'up':
                        filters.append(f"Major冠军 > {field_value} (数值偏小 ↑)")
                        candidates = [p for p in candidates if p['major_championships'] > field_value]
                    elif direction == 'down':
                        filters.append(f"Major冠军 < {field_value} (数值偏大 ↓)")
                        candidates = [p for p in candidates if p['major_championships'] < field_value]
                elif field == 'major_appearances':
                    if direction == 'up':
                        filters.append(f"Major次数 > {field_value} (数值偏小 ↑)")
                        candidates = [p for p in candidates if p['major_appearances'] > field_value]
                    elif direction == 'down':
                        filters.append(f"Major次数 < {field_value} (数值偏大 ↓)")
                        candidates = [p for p in candidates if p['major_appearances'] < field_value]
            
            elif status == 'wrong' and not direction:
                # 错误但没有方向指示（排除该值）
                if field == 'nickname':
                    filters.append(f"排除昵称 = {field_value}")
                    candidates = [p for p in candidates if p['nickname'].lower() != field_value.lower()]
                elif field == 'team':
                    filters.append(f"排除队伍 = {field_value}")
                    candidates = [p for p in candidates if p['team'] != mapped_value]
                elif field == 'nationality':
                    target_region = self.get_region_by_nationality(field_value)
                    if target_region and target_region != "未知":
                        filters.append(f"剔除赛区 = {target_region} (国家:{field_value} 错误)")
                        candidates = [p for p in candidates if p.get('region', '') != target_region]
                    else:
                        filters.append(f"排除国籍 = {field_value}")
                        candidates = [p for p in candidates if p['nationality'] != field_value]
                elif field == 'role':
                    filters.append(f"排除位置 = {field_value}")
                    candidates = [p for p in candidates if p['role'] != mapped_value]
                elif field == 'age':
                    filters.append(f"排除年龄 = {field_value}")
                    candidates = [p for p in candidates if p['age'] != field_value]
                elif field == 'major_championships':
                    filters.append(f"排除Major冠军 = {field_value}")
                    candidates = [p for p in candidates if p['major_championships'] != field_value]
                elif field == 'major_appearances':
                    filters.append(f"排除Major次数 = {field_value}")
                    candidates = [p for p in candidates if p['major_appearances'] != field_value]
                elif field == 'is_active':
                    filters.append(f"排除状态 = {field_value}")
                    candidates = [p for p in candidates if p['is_active'] != mapped_value]
        
        print(f"  应用了 {len(filters)} 个筛选条件")
        for f in filters:
            print(f"    • {f}")
        
        print(f"  ✅ 剩余 {len(candidates)} 名候选选手")
        return candidates

# ---------- GUI 显示窗口 ----------
class CandidateWindow:
    def __init__(self, on_reset_callback=None):
        self.root = None
        self.tree = None
        self.status_label = None
        self.window_open = False
        self.lock = threading.Lock()
        self.on_reset_callback = on_reset_callback
        self.current_candidates = []
        self.current_filters = []
        self.page_size = 50
        self.current_page = 0
        self.total_pages = 0
        
        self.page_label = None
        self.prev_btn = None
        self.next_btn = None
        self.page_entry = None
    
    def create_window(self):
        if self.window_open:
            return
        
        self.root = tk.Tk()
        self.root.title("🎯 候选选手列表")
        self.root.geometry("950x700")
        self.root.attributes('-topmost', True)
        self.window_open = True
        
        title_label = ttk.Label(self.root, text="🎯 候选选手筛选器", font=("Arial", 14, "bold"))
        title_label.pack(pady=5)
        
        self.status_label = ttk.Label(self.root, text="等待筛选...", font=("Arial", 10))
        self.status_label.pack(pady=5)
        
        frame = ttk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ("昵称", "国籍", "赛区", "队伍", "年龄", "位置", "Major冠", "Major次", "状态")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=20)
        
        col_widths = [100, 70, 70, 100, 50, 80, 70, 70, 60]
        for col, width in zip(columns, col_widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor=tk.CENTER)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 分页控件
        page_frame = ttk.Frame(self.root)
        page_frame.pack(pady=5)
        
        self.prev_btn = ttk.Button(page_frame, text="◀ 上一页", command=self.prev_page)
        self.prev_btn.pack(side=tk.LEFT, padx=5)
        
        self.page_label = ttk.Label(page_frame, text="第 1 / 1 页", font=("Arial", 10))
        self.page_label.pack(side=tk.LEFT, padx=10)
        
        self.next_btn = ttk.Button(page_frame, text="下一页 ▶", command=self.next_page)
        self.next_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(page_frame, text="跳转到:").pack(side=tk.LEFT, padx=5)
        self.page_entry = ttk.Entry(page_frame, width=5)
        self.page_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(page_frame, text="GO", command=self.go_to_page).pack(side=tk.LEFT, padx=5)
        
        # 底部按钮
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=10)
        
        reset_btn = ttk.Button(btn_frame, text="🔄 新的一轮", 
                               command=self.reset_round, 
                               style="Accent.TButton")
        reset_btn.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(btn_frame, text="刷新", command=self.refresh).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空", command=self.clear).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=self.close).pack(side=tk.LEFT, padx=5)
        
        style = ttk.Style()
        style.configure("Accent.TButton", foreground="green", font=("Arial", 10, "bold"))
        
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.mainloop()
    
    def _update_ui_safe(self, func, *args):
        if self.root and self.window_open:
            try:
                self.root.after(0, lambda: func(*args))
            except Exception as e:
                print(f"⚠️ UI更新失败: {e}")
    
    def _display_page(self):
        try:
            if not self.tree:
                return
            
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            if not self.current_candidates:
                return
            
            start = self.current_page * self.page_size
            end = min(start + self.page_size, len(self.current_candidates))
            page_data = self.current_candidates[start:end]
            
            for p in page_data:
                status = "现役" if p.get('is_active', False) else "退役"
                self.tree.insert("", tk.END, values=(
                    p.get('nickname', '-'),
                    p.get('nationality', '-'),
                    p.get('region', '-'),
                    p.get('team', '-'),
                    p.get('age', '-'),
                    p.get('role', '-'),
                    p.get('major_championships', 0),
                    p.get('major_appearances', 0),
                    status
                ))
            
            self.total_pages = (len(self.current_candidates) + self.page_size - 1) // self.page_size
            if self.page_label:
                self.page_label.config(text=f"第 {self.current_page + 1} / {self.total_pages} 页")
            
            if self.prev_btn:
                self.prev_btn.config(state=tk.NORMAL if self.current_page > 0 else tk.DISABLED)
            if self.next_btn:
                self.next_btn.config(state=tk.NORMAL if self.current_page < self.total_pages - 1 else tk.DISABLED)
            
            if self.status_label:
                filter_text = f"✅ 共 {len(self.current_candidates)} 名候选选手"
                if self.current_filters:
                    filter_text += f" | 筛选条件: {', '.join(self.current_filters[:3])}"
                    if len(self.current_filters) > 3:
                        filter_text += f" ... (+{len(self.current_filters)-3})"
                self.status_label.config(text=filter_text)
        except Exception as e:
            print(f"⚠️ 显示页面失败: {e}")
    
    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._display_page()
    
    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._display_page()
    
    def go_to_page(self):
        try:
            page = int(self.page_entry.get()) - 1
            if 0 <= page < self.total_pages:
                self.current_page = page
                self._display_page()
            else:
                self.page_entry.delete(0, tk.END)
                self.page_entry.insert(0, str(self.current_page + 1))
        except ValueError:
            pass
    
    def reset_round(self):
        print("\n🔄 用户点击了'新的一轮'按钮")
        
        if self.status_label:
            self.status_label.config(text="🔄 新的一轮已开始，等待新的猜测...")
        self.current_page = 0
        
        if self.tree:
            for item in self.tree.get_children():
                self.tree.delete(item)
        
        if self.on_reset_callback:
            self.on_reset_callback()
    
    def update_candidates(self, candidates: List[dict], filters: List[str] = None):
        with self.lock:
            self.current_candidates = candidates
            self.current_filters = filters or []
            self.current_page = 0
            self._update_ui_safe(self._display_page)
    
    def refresh(self):
        if self.current_candidates:
            self.update_candidates(self.current_candidates, self.current_filters)
    
    def clear(self):
        with self.lock:
            if self.tree:
                for item in self.tree.get_children():
                    self.tree.delete(item)
            if self.status_label:
                self.status_label.config(text="已清空，点击'新的一轮'重新开始")
            self.current_candidates = []
            self.current_filters = []
            self.current_page = 0
            self.total_pages = 0
            if self.page_label:
                self.page_label.config(text="第 0 / 0 页")
    
    def close(self):
        self.window_open = False
        if self.root:
            try:
                self.root.destroy()
            except:
                pass
            self.root = None

# ---------- 主程序 ----------
class GameMonitor:
    def __init__(self, url: str):
        self.url = url
        self.driver = None
        self.db = PlayerDB("players.json")
        self.candidate_window = None
        self.last_row_count = 0
        self.is_running = False
        self.current_round = 0
        
        self._init_driver()
    
    def _init_driver(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--start-maximized")
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.get(self.url)
            print(f"✅ 浏览器已启动，正在访问: {self.url}")
        except Exception as e:
            print(f"❌ 浏览器启动失败: {e}")
            traceback.print_exc()
            raise
    
    def reset_round(self):
        self.current_round += 1
        self.last_row_count = 0
        print(f"\n{'='*60}")
        print(f"🔄 第 {self.current_round} 轮开始")
        print(f"{'='*60}")
        
        if self.candidate_window and self.candidate_window.window_open:
            print("📋 加载所有选手...")
            all_players = self.db.players.copy()
            self.candidate_window.update_candidates(all_players, ["新的一轮 - 显示所有选手"])
            print(f"✅ 已加载 {len(all_players)} 名选手")
    
    def get_table_data(self) -> List[dict]:
        try:
            wait = WebDriverWait(self.driver, 5)
            table = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "game-table")))
            rows = table.find_elements(By.XPATH, ".//tbody/tr")
            
            all_rows_data = []
            
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if not cells:
                    continue
                
                row_data = {}
                
                for cell in cells:
                    label = cell.get_attribute("data-label")
                    if not label:
                        continue
                    
                    classes = cell.get_attribute("class").split()
                    status_class = [c for c in classes if c in ['correct', 'close', 'wrong']]
                    
                    text = cell.text.strip()
                    
                    # ====== 修复：正确识别箭头方向 ======
                    direction = None
                    try:
                        dir_span = cell.find_element(By.XPATH, ".//span[@class='dir']")
                        if dir_span:
                            # 方法1：通过 SVG 的 class 判断
                            svg = dir_span.find_element(By.TAG_NAME, "svg")
                            if svg:
                                svg_class = svg.get_attribute("class")
                                if svg_class:
                                    if 'arrow-up' in svg_class:
                                        direction = 'up'
                                    elif 'arrow-down' in svg_class:
                                        direction = 'down'
                                
                                # 方法2：如果 class 没有，通过 path 的 d 属性判断
                                if not direction:
                                    try:
                                        path = svg.find_element(By.TAG_NAME, "path")
                                        d = path.get_attribute("d")
                                        if d:
                                            # arrow-up 的路径特征
                                            if 'm5 12 7-7 7 7' in d or 'M12 19v-14' in d:
                                                direction = 'up'
                                            # arrow-down 的路径特征
                                            elif 'M12 5v14' in d or 'm19 12-7 7-7-7' in d:
                                                direction = 'down'
                                    except:
                                        pass
                    except:
                        pass
                    
                    field_map = {
                        '昵称': 'nickname',
                        '队伍': 'team',
                        '国家或地区': 'nationality',
                        '年龄': 'age',
                        '位置': 'role',
                        'Major 冠军': 'major_championships',
                        'Major 次数': 'major_appearances',
                        '状态': 'is_active'
                    }
                    
                    field_name = field_map.get(label)
                    if field_name:
                        if field_name in ['age', 'major_championships', 'major_appearances']:
                            digits = re.search(r'\d+', text)
                            if digits:
                                row_data[field_name] = int(digits.group())
                            else:
                                row_data[field_name] = text
                        elif field_name == 'is_active':
                            row_data[field_name] = text
                        else:
                            row_data[field_name] = text
                        
                        if status_class:
                            row_data[f'{field_name}_status'] = status_class[0]
                        if direction:
                            row_data[f'{field_name}_direction'] = direction
                
                is_latest = 'row-latest' in row.get_attribute("class")
                row_data['is_latest'] = is_latest
                
                if row_data:
                    all_rows_data.append(row_data)
            
            return all_rows_data
            
        except Exception as e:
            print(f"⚠️ 提取表格数据失败: {e}")
            return []
    
    def process_guess(self, all_rows: list, row_index: int):
        """处理一次猜测，结合所有历史行进行筛选"""
        try:
            if row_index > len(all_rows):
                return
            
            current_row = all_rows[row_index - 1]
            
            print(f"\n🔔 处理第 {row_index} 次猜测 (第{self.current_round}轮)...")
            print(f"  昵称: {current_row.get('nickname', '-')}")
            status = current_row.get('age_status', '-')
            print(f"  状态: {status}")
            
            # ====== 累积所有历史行的数据 ======
            accumulated_data = {}
            
            for i in range(row_index):
                row = all_rows[i]
                for key, value in row.items():
                    if value is None or value == '':
                        continue
                        
                    if key.endswith('_status') or key.endswith('_direction'):
                        # 状态和方向：只保留最新的
                        accumulated_data[key] = value
                    else:
                        # 普通字段：保留最新的非空值
                        if i == row_index - 1:
                            accumulated_data[key] = value
                        elif key not in accumulated_data or accumulated_data.get(key) is None:
                            accumulated_data[key] = value
            
            # 打印累积的数据（调试用）
            print(f"\n📊 累积的筛选条件:")
            for key, value in accumulated_data.items():
                if not key.endswith('_status') and not key.endswith('_direction'):
                    status_key = f'{key}_status'
                    dir_key = f'{key}_direction'
                    status_str = f" [{accumulated_data.get(status_key, '')}]" if status_key in accumulated_data else ""
                    dir_str = f" {accumulated_data.get(dir_key, '')}" if dir_key in accumulated_data else ""
                    if value is not None and value != '':
                        print(f"  {key}: {value}{status_str}{dir_str}")
            
            # 使用累积的数据进行筛选
            candidates = self.db.filter_candidates(accumulated_data)
            
            # 提取筛选条件用于显示
            filters = []
            for field in ['nickname', 'team', 'nationality', 'age', 'role', 
                          'major_championships', 'major_appearances']:
                status_field = accumulated_data.get(f'{field}_status')
                if status_field:
                    value = accumulated_data.get(field)
                    if value is not None and value != '':
                        filters.append(f"{field}={value}")
            
            if self.candidate_window and self.candidate_window.window_open:
                self.candidate_window.update_candidates(candidates, filters[:5])
            
            print(f"\n📋 候选选手（前10名）:")
            for i, p in enumerate(candidates[:10], 1):
                print(f"  {i}. {p['nickname']} | {p['team']} | {p['nationality']} | {p['age']}岁")
            if len(candidates) > 10:
                print(f"  ... 还有 {len(candidates)-10} 名选手")
            if len(candidates) == 0:
                print(f"  ❌ 没有符合条件的选手，点击'新的一轮'重新开始")
        except Exception as e:
            print(f"❌ 处理猜测失败: {e}")
            traceback.print_exc()
    
    def monitor_loop(self, interval: float = 2.0):
        self.is_running = True
        self.last_row_count = 0
        self.current_round = 1
        
        print("\n🖥️ 正在打开候选选手窗口...")
        self.candidate_window = CandidateWindow(on_reset_callback=self.reset_round)
        window_thread = threading.Thread(target=self.candidate_window.create_window, daemon=True)
        window_thread.start()
        
        time.sleep(1)
        
        print("\n📋 初始显示所有选手...")
        if self.candidate_window and self.candidate_window.window_open:
            all_players = self.db.players.copy()
            self.candidate_window.update_candidates(all_players, ["新的一轮 - 显示所有选手"])
            print(f"✅ 已加载 {len(all_players)} 名选手 (分页显示，每页50条)")
        
        print(f"\n🔍 开始持续监控（每 {interval} 秒检测一次）")
        print("💡 每次猜测后会自动更新候选列表")
        print("📌 在候选窗口点击'新的一轮'可重置筛选")
        print("📌 按 Ctrl+C 停止监控\n")
        
        try:
            while self.is_running:
                try:
                    all_rows = self.get_table_data()
                    current_count = len(all_rows)
                    
                    if current_count > self.last_row_count:
                        new_rows = all_rows[self.last_row_count:]
                        for i, row in enumerate(new_rows, self.last_row_count + 1):
                            self.process_guess(all_rows, i)
                        
                        self.last_row_count = current_count
                    
                    time.sleep(interval)
                except Exception as e:
                    print(f"⚠️ 监控循环异常: {e}")
                    traceback.print_exc()
                    time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n🛑 监控已停止")
            self.is_running = False
    
    def close(self):
        self.is_running = False
        if self.candidate_window:
            self.candidate_window.close()
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

# ---------- 启动 ----------
def main():
    GAME_URL = "https://shnlfriberg.online/"
    
    try:
        monitor = GameMonitor(GAME_URL)
        
        try:
            input("\n请在浏览器中完成所有操作（登录、进入游戏对局等），然后按 Enter 开始...")
            monitor.monitor_loop(interval=2.0)
        except KeyboardInterrupt:
            print("\n🛑 用户中断")
        finally:
            monitor.close()
            print("✅ 程序已退出")
    except Exception as e:
        print(f"❌ 程序启动失败: {e}")
        traceback.print_exc()
        input("\n按 Enter 退出...")


if __name__ == "__main__":
    main()