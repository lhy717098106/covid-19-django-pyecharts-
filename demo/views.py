import json

import pandas as pd
import requests
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from pyecharts.components import Table
from pyecharts.globals import CurrentConfig, ChartType, SymbolType
from django.http import HttpResponse

# Create your views here.

from pyecharts.charts import Geo, Timeline, Map, Line, Tab, Grid
import pymongo
from pyecharts import options as opts
import akshare as ak
import datetime

CurrentConfig.GLOBAL_ENV = Environment(loader=FileSystemLoader("./demo/templates"))


def dateRange(start, end, step=1, format="%Y-%m-%d"):
    strptime, strftime = datetime.datetime.strptime, datetime.datetime.strftime
    days = (strptime(end, format) - strptime(start, format)).days
    return [strftime(strptime(start, format) + datetime.timedelta(i), format) for i in range(0, days, step)]


def line_datazoom_slider():
    covid_19_163_df = ak.covid_19_163(indicator="中国历史时点数据")

    l = list(covid_19_163_df.index)
    l0 = list(covid_19_163_df["confirm"])
    l1 = list(covid_19_163_df["suspect"])
    l2 = list(covid_19_163_df["input"])
    l3 = list(covid_19_163_df["heal"])
    c = (
        Line()
            .add_xaxis(xaxis_data=list(covid_19_163_df.index))
            .add_yaxis(
            series_name="confirm",
            y_axis=list(covid_19_163_df["confirm"]),
            yaxis_index=0,
            is_smooth=True,
            is_symbol_show=False,
        )

            .set_global_opts(
            title_opts=opts.TitleOpts(title="60日确诊变化"),
            tooltip_opts=opts.TooltipOpts(trigger="axis"),
            datazoom_opts=[
                opts.DataZoomOpts(yaxis_index=0),
                opts.DataZoomOpts(type_="inside", yaxis_index=0),
            ],
            visualmap_opts=opts.VisualMapOpts(
                pos_top="10",
                pos_right="10",
                is_piecewise=True,
                pieces=[
                    {"gt": 0, "lte": 50, "color": "#096"},
                    {"gt": 50, "lte": 100, "color": "#ffde33"},
                    {"gt": 100, "lte": 150, "color": "#ff9933"},
                    {"gt": 150, "lte": 200, "color": "#cc0033"},
                    {"gt": 200, "lte": 300, "color": "#660099"},
                    {"gt": 300, "color": "#7e0023"},
                ],
                out_of_range={"color": "#999"},
            ),
            xaxis_opts=opts.AxisOpts(type_="category"),
            yaxis_opts=opts.AxisOpts(
                type_="value",
                name_location="start",
                min_=0,
                max_=500,
                is_scale=True,
                axistick_opts=opts.AxisTickOpts(is_inside=False),
            ),
        )
            .set_series_opts(
            markline_opts=opts.MarkLineOpts(
                data=[
                    {"yAxis": 100},
                    {"yAxis": 200},
                    {"yAxis": 300},
                    {"yAxis": 400},
                    {"yAxis": 500},
                ],
                label_opts=opts.LabelOpts(position="end"),
            )
        )

    )
    return c


def country():
    t2 = Timeline()
    client = pymongo.MongoClient(host='localhost', port=27017)
    db = client.mongodb_database
    collection = db.table
    for date in dateRange("2019-12-10", "2020-06-01"):
        try:
            pipeline = [{'$match': {'date': {"$eq": date}}}, {
                '$group': {'_id': "$province", 'count': {'$sum': '$confirmed'}, 'count1': {'$sum': '$cured'},
                           'count2': {'$sum': '$dead'}}}]
            xy = collection.aggregate(pipeline)
            data = []
            for i in xy:
                data.append((i["_id"].replace("省", "").replace("回族", "").replace("市", "").replace("自治区", "").replace(
                    "维吾尔", "").replace("壮族", ""), i["count"] - i["count1"] - i["count2"]))

            _map = (
                Map()
                    .add("销售额", data, "china")
                    .set_global_opts(
                    title_opts=opts.TitleOpts(title="全国疫情变化"),
                    legend_opts=opts.LegendOpts(is_show=False),
                    visualmap_opts=opts.VisualMapOpts(is_piecewise=True, pieces=[
                        {"min": 3000, "label": '>450人', "color": "#f00303"},
                        {"min": 2500, "max": 3000, "label": '400-450人', "color": "#f04a03"},
                        # 不指定 max，表示 max 为无限大（Infinity）。
                        {"min": 1500, "max": 2000, "label": '300-400人', "color": "#f0b103"},
                        {"min": 1000, "max": 1500, "label": '200-300人', "color": "#e8f003"},
                        {"min": 500, "max": 1000, "label": '100-200人', "color": "#1ff003"},
                        {"min": 1, "max": 500, "label": '1-99人', "color": "#03e4f0"},
                    ], ),
                )
            )

            t2.add(_map, "{}".format(date))

        except:
            print(date)

    return t2


def province(province):
    client = pymongo.MongoClient(host='localhost', port=27017)
    db = client.mongodb_database
    collection = db.table
    tl = Timeline()
    for date in dateRange("2019-12-20", "2020-06-01"):
        try:
            price = collection.find({"date": date, "province": province, },
                                    {'_id': 0, "city": 1, 'confirmed': 1, "suspected": 1, "cured": 1, "dead": 1})
            az = []
            for i in price:
                if i["city"] == "境外输入":
                    continue
                az.append((i["city"], i["confirmed"] + i["suspected"] - i["dead"] - i["cured"]))
            c = (
                Map()
                    .add("", az, province.replace("省", "").replace("市", ""))
                    .set_global_opts(
                    title_opts=opts.TitleOpts(title=province + "疫情变化"),
                    visualmap_opts=opts.VisualMapOpts(max_=2000),
                )
            )
            tl.add(c, "{}".format(date))
        except:
            continue
    return tl


def news():
    url = "https://3g.dxy.cn/newh5/view/pneumonia"
    r = requests.get(url)
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "lxml")
    # news-china
    text_data_news = str(soup.find("script", attrs={"id": "getTimelineService1"}))
    temp_json = text_data_news[text_data_news.find("= [{") + 2: text_data_news.rfind("}catch")
                ]
    json_data = pd.DataFrame(json.loads(temp_json))
    chinese_news = json_data[
        [
            "id",
            "pubDate",
            "pubDateStr",
            "title",
            "summary",
            "infoSource",
            "sourceUrl",
            "provinceId",
        ]
    ]

    table = Table()
    data = chinese_news.to_dict(orient='records')
    headers = ["pubDate", "title", "url"]
    mylist = []
    for i in data:
        mylist.append([i["pubDateStr"], i["title"], i["sourceUrl"]])
    table.add(headers, mylist)
    return table


def qianru(date: "20200101"):
    client = pymongo.MongoClient(host='localhost', port=27017)
    db = client.mongodb_database
    collection = db.move_in

    price = collection.find({"date": date}, {'_id': 0, "city_name": 1, "value": 1})
    move = []
    movedata = []
    for i in price[:20]:
        move.append((i["city_name"], "湖北"))
        movedata.append((i["city_name"], i["value"]))

    c = (
        Geo()
            .add_schema(
            maptype="china",
            itemstyle_opts=opts.ItemStyleOpts(color="#dbe6b8", border_color="#111"),
        )
            .add(
            "",
            movedata,
            type_=ChartType.EFFECT_SCATTER,
            color="white",
        )
            .add(
            "迁入",
            move,
            type_=ChartType.LINES,
            effect_opts=opts.EffectOpts(
                symbol=SymbolType.ARROW, symbol_size=6, color="blue"
            ),
            linestyle_opts=opts.LineStyleOpts(curve=0.2),
        )
            .set_series_opts(label_opts=opts.LabelOpts(is_show=False))
            .set_global_opts(title_opts=opts.TitleOpts(title="迁出"), legend_opts=opts.LegendOpts(pos_right="60%"), )
    )

    return c


def qianchu(date: "20200101"):
    client = pymongo.MongoClient(host='localhost', port=27017)
    db = client.mongodb_database
    collection = db.qianxi

    price = collection.find({"date": date}, {'_id': 0, "city_name": 1, "value": 1})
    move = []
    movedata = []
    for i in price[:20]:
        move.append(("武汉", i["city_name"]))
        movedata.append((i["city_name"], i["value"]))

    c1 = (
        Geo()
            .add_schema(
            maptype="china",
            itemstyle_opts=opts.ItemStyleOpts(color="#dbe6b8", border_color="#111"),
        )
            .add(
            "",
            movedata,
            type_=ChartType.EFFECT_SCATTER,
            color="white",
        )
            .add(
            "迁出",
            move,
            type_=ChartType.LINES,
            effect_opts=opts.EffectOpts(
                symbol=SymbolType.ARROW, symbol_size=6, color="blue"
            ),
            linestyle_opts=opts.LineStyleOpts(curve=0.2),
        )
            .set_series_opts(label_opts=opts.LabelOpts(is_show=False))
            .set_global_opts(title_opts=opts.TitleOpts(title="迁出"))
            .set_global_opts(

            legend_opts=opts.LegendOpts(pos_left="60%"),
        ))
    return c1


def index(request):
    tab = Tab()
    tab.add(country(), "中国")
    tab.add(province("湖北省"), "湖北省")
    tab.add(province("广东省"), "广东省")
    tab.add(province("河南省"), "河南省")
    tab.add(province("浙江省"), "浙江省")
    tab.add(province("山西省"), "山西省")
    tab.add(news(), "最新消息")
    return HttpResponse(tab.render_embed("index.html"))


def search(request):
    title = request.GET.get('searchtext')  # 得到搜索内容
    if title == None:
        title = "20200101"
    grid = (
        Grid(init_opts=opts.InitOpts(width="1200px", height="600px"))
            .add(qianru(title), grid_opts=opts.GridOpts(pos_left="30%"))
            .add(qianchu(title), grid_opts=opts.GridOpts(pos_right="55%"))

    )

    return HttpResponse(grid.render_embed("simple_chart.html"))
