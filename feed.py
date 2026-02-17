import feedparser
import os
import time
import requests
from dotenv import load_dotenv
from helpers import time_difference

load_dotenv()

RUN_FREQUENCY = int(os.getenv("RUN_FREQUENCY", "3600"))

# ===== 曼联 RSS 源（包含主流媒体 + RSSHub 微信/抖音/B站/微博）=====
RSS_URLS = [
    # Google News 多关键词搜索（基础）
    "https://news.google.com/rss/search?q=Manchester+United+OR+%E6%9B%BC%E8%81%94+OR+%E7%BA%A2%E9%AD%94+OR+MUFC+OR+%E6%9B%BC%E5%BD%BB%E6%96%AF%E7%89%B9%E8%81%94+OR+Man+Utd+OR+%E6%A0%BC%E6%9E%97%E4%BC%8D%E5%BE%B7&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",

    # 主流体育媒体
    "http://feeds.bbci.co.uk/sport/football/teams/manchester-united/rss.xml",
    "https://www.skysports.com/feeds/teams/manchester-united",
    "https://www.espn.com/espn/rss/teams/news?id=360",
    "https://www.theguardian.com/football/manchester-united/rss",
    "https://www.telegraph.co.uk/sport/football/teams/manchester-united/rss",

    # 俱乐部官方
    "https://www.manutd.com/feed",

    # 球迷社区
    "https://www.reddit.com/r/reddevils/.rss",

    # 国内体育媒体
    "https://sports.sina.com.cn/global/manchesterunited/feed/",
    "https://www.dongqiudi.com/teams/5/feed/",

    # RSSHub 生成的社交媒体搜索
    "https://rsshub.app/wechat/search/曼联",
    "https://rsshub.app/douyin/search/曼联",
    "https://rsshub.app/bilibili/vsearch/曼联",
    "https://rsshub.app/weibo/search/曼联",
]

def _parse_struct_time_to_timestamp(st):
    if st:
        return time.mktime(st)
    return 0

def send_feishu_message(text):
    webhook_url = os.getenv("FEISHU_WEBHOOK")
    if not webhook_url:
        print("❌ 环境变量 FEISHU_WEBHOOK 未设置")
        return
    payload = {
        "msg_type": "text",
        "content": {"text": text}
    }
    try:
        resp = requests.post(webhook_url, json=payload)
        if resp.status_code == 200:
            print("✅ 飞书消息发送成功")
        else:
            print(f"❌ 飞书消息发送失败: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ 飞书请求异常: {e}")

def get_new_feed_items_from(feed_url):
    print(f"正在抓取 RSS: {feed_url}")
    try:
        rss = feedparser.parse(feed_url)
        print(f"RSS 解析成功，条目总数: {len(rss.entries)}")
    except Exception as e:
        print(f"Error parsing feed {feed_url}: {e}")
        return []

    current_time_struct = rss.get("updated_parsed") or rss.get("published_parsed")
    current_time = _parse_struct_time_to_timestamp(current_time_struct) if current_time_struct else time.time()

    new_items = []
    for item in rss.entries:
        pub_date = item.get("published_parsed") or item.get("updated_parsed")
        if pub_date:
            blog_published_time = _parse_struct_time_to_timestamp(pub_date)
        else:
            continue

        diff = time_difference(current_time, blog_published_time)
        if diff["diffInSeconds"] < RUN_FREQUENCY:
            new_items.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "content": item.get("content", [{}])[0].get("value", item.get("summary", "")),
                "published_parsed": pub_date
            })

    print(f"本次抓取到 {len(new_items)} 条新文章")
    return new_items

def get_new_feed_items():
    all_new_feed_items = []
    for feed_url in RSS_URLS:
        feed_items = get_new_feed_items_from(feed_url)
        all_new_feed_items.extend(feed_items)

    all_new_feed_items.sort(
        key=lambda x: _parse_struct_time_to_timestamp(x.get("published_parsed"))
    )
    print(f"总共 {len(all_new_feed_items)} 条新文章待推送")

    for item in all_new_feed_items:
        text = f"{item['title']}\n{item['link']}"
        send_feishu_message(text)

    return all_new_feed_items
