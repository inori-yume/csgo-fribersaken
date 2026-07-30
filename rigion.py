# analyze_players.py
import json
from collections import defaultdict

def analyze_players(json_file="players.json"):
    """分析选手数据，统计国籍和赛区分布"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                players = data
            elif isinstance(data, dict) and 'players' in data:
                players = data['players']
            else:
                players = []
        
        print(f"📊 共有 {len(players)} 名选手")
        print("="*60)
        
        # 统计国籍分布
        nationality_count = defaultdict(int)
        region_count = defaultdict(int)
        nationality_region = defaultdict(set)
        
        for p in players:
            if p.get('is_enabled', True):
                nat = p.get('nationality', '未知')
                region = p.get('region', '未知')
                nationality_count[nat] += 1
                region_count[region] += 1
                nationality_region[nat].add(region)
        
        # 打印国籍统计
        print("\n🌍 国籍分布（按数量排序）:")
        for nat, count in sorted(nationality_count.items(), key=lambda x: x[1], reverse=True):
            regions = nationality_region[nat]
            region_str = ', '.join(regions)
            print(f"  {nat}: {count} 人 → 赛区: {region_str}")
        
        # 打印赛区统计
        print("\n🏆 赛区分布:")
        for region, count in sorted(region_count.items(), key=lambda x: x[1], reverse=True):
            print(f"  {region}: {count} 人")
        
        # 生成国籍→赛区映射（用于代码）
        print("\n📝 国籍→赛区映射（可直接复制到代码中）:")
        print("NATIONALITY_TO_REGION = {")
        for nat, regions in sorted(nationality_region.items()):
            # 如果一个国籍对应多个赛区，取第一个
            region = list(regions)[0] if regions else '未知'
            print(f'    "{nat}": "{region}",')
        print("}")
        
        # 检查是否有国籍对应多个赛区
        print("\n⚠️ 多赛区国籍（一个国籍对应多个赛区）:")
        multi_region = {nat: regions for nat, regions in nationality_region.items() if len(regions) > 1}
        if multi_region:
            for nat, regions in multi_region.items():
                print(f"  {nat}: {regions}")
        else:
            print("  ✅ 没有多赛区国籍")
        
        return nationality_region
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        return {}

if __name__ == "__main__":
    analyze_players("players.json")