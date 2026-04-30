import io
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.font_manager as fm
from sentence_transformers import SentenceTransformer

# =====================================
# 0. 统一论文绘图风格（中文优先）
# =====================================
def setup_style():
    preferred = [
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "Microsoft YaHei",
        "PingFang SC",
        "SimHei",
        "WenQuanYi Micro Hei",
        "Arial Unicode MS",
    ]
    available = {f.name for f in fm.fontManager.ttflist}

    for fnt in preferred:
        if fnt in available:
            mpl.rcParams["font.family"] = "sans-serif"
            mpl.rcParams["font.sans-serif"] = [fnt, "DejaVu Sans"]
            break
    else:
        mpl.rcParams["font.family"] = "sans-serif"
        mpl.rcParams["font.sans-serif"] = ["DejaVu Sans"]

    mpl.rcParams["axes.unicode_minus"] = False
    mpl.rcParams["pdf.fonttype"] = 42
    mpl.rcParams["ps.fonttype"] = 42
    mpl.rcParams["figure.dpi"] = 120
    mpl.rcParams["savefig.dpi"] = 600

    # 坐标轴与网格
    mpl.rcParams["axes.spines.top"] = False
    mpl.rcParams["axes.spines.right"] = False
    mpl.rcParams["axes.linewidth"] = 1.0

    mpl.rcParams["axes.labelsize"] = 11
    mpl.rcParams["xtick.labelsize"] = 9
    mpl.rcParams["ytick.labelsize"] = 9
    mpl.rcParams["legend.fontsize"] = 9

    mpl.rcParams["axes.grid"] = True
    mpl.rcParams["grid.alpha"] = 0.20
    mpl.rcParams["grid.linewidth"] = 0.7

def load_data(raw_data):
    """读取字符串并加载为 DataFrame"""
    df = pd.read_csv(
        io.StringIO(raw_data.strip()),
        sep="\t",
        header=None,
        names=["en_query", "zh_query"]
    ).dropna()
    print(f"Loaded {len(df)} query pairs from raw string.")
    return df

def load_from_excel(excel_path):
    """从 Excel 文件中加载数据"""
    if not os.path.exists(excel_path):
        print(f"Excel file not found: {excel_path}")
        return pd.DataFrame()
    
    # 读取 Excel，假定包含 'rumor' 和 'chinese' 列
    df_excel = pd.read_excel(excel_path)
    if 'rumor' in df_excel.columns and 'chinese' in df_excel.columns:
        df = df_excel[['rumor', 'chinese']].rename(columns={'rumor': 'en_query', 'chinese': 'zh_query'}).dropna()
        print(f"Loaded {len(df)} query pairs from Excel: {excel_path}")
        return df
    else:
        print(f"Excel file must contain 'rumor' and 'chinese' columns.")
        return pd.DataFrame()

def analyze_similarity(df):
    """计算中英查询的语义相似度并绘图"""
    # 加载多语言嵌入模型
    model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")

    # 编码
    en_embeddings = model.encode(
        df["en_query"].tolist(),
        normalize_embeddings=True,
        show_progress_bar=True
    )
    zh_embeddings = model.encode(
        df["zh_query"].tolist(),
        normalize_embeddings=True,
        show_progress_bar=True
    )

    # 计算余弦相似度
    cosine_similarity = np.sum(en_embeddings * zh_embeddings, axis=1)

    # 输出统计值
    mean_val = cosine_similarity.mean()
    median_val = np.median(cosine_similarity)
    min_val = cosine_similarity.min()
    max_val = cosine_similarity.max()

    print(f"Mean cosine similarity: {mean_val:.4f}")
    print(f"Median cosine similarity: {median_val:.4f}")
    print(f"Min cosine similarity: {min_val:.4f}")
    print(f"Max cosine similarity: {max_val:.4f}")

    return cosine_similarity, mean_val, median_val, min_val, max_val

def plot_similarity(cosine_similarity, mean_val, median_val, min_val, max_val, out_dir):
    """绘制相似度分布图并保存"""
    MAIN_BLUE = "#4E79A7"
    MEAN_LINE = "#F28E2B"
    MEDIAN_LINE = "#59A14F"

    fig, ax = plt.subplots(figsize=(6.8, 4.2))

    # 每个样本贡献 100/N，实现 y 轴百分比
    weights = np.ones_like(cosine_similarity) * 100.0 / len(cosine_similarity)

    ax.hist(
        cosine_similarity,
        bins=20,
        weights=weights,
        color=MAIN_BLUE,
        edgecolor="white",
        linewidth=0.8,
        alpha=0.90
    )

    # 均值 / 中位数参考线
    ax.axvline(
        mean_val,
        linestyle="--",
        linewidth=1.6,
        color=MEAN_LINE,
        label=f"均值 = {mean_val:.3f}"
    )
    ax.axvline(
        median_val,
        linestyle=":",
        linewidth=1.8,
        color=MEDIAN_LINE,
        label=f"中位数 = {median_val:.3f}"
    )

    # 坐标轴
    ax.set_xlabel("中英查询语义相似度")
    ax.set_ylabel("占比（%）")

    # 统一范围
    ax.set_xlim(max(0.0, min_val - 0.02), min(1.0, max_val + 0.02))

    # 只保留 y 方向网格
    ax.grid(True, axis="y")
    ax.grid(False, axis="x")

    # 图例
    ax.legend(
        frameon=False,
        ncol=2,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.12)
    )

    fig.subplots_adjust(top=0.84)

    os.makedirs(out_dir, exist_ok=True)
    png_path = os.path.join(out_dir, "en_zh_similarity_distribution_percent.png")
    pdf_path = os.path.join(out_dir, "en_zh_similarity_distribution_percent.pdf")

    fig.savefig(png_path, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.show()
    plt.close(fig)

    print("Saved:")
    print(png_path)
    print(pdf_path)

def main(input_data, output_dir):
    """主函数：规范化结构"""
    setup_style()
    # 根据输入类型加载数据
    if isinstance(input_data, str) and (input_data.endswith('.xlsx') or input_data.endswith('.xls')):
        df = load_from_excel(input_data)
    else:
        df = load_data(input_data)
    
    if df is not None and not df.empty:
        sim_data, mean_v, median_v, min_v, max_v = analyze_similarity(df)
        plot_similarity(sim_data, mean_v, median_v, min_v, max_v, output_dir)
    else:
        print("No data loaded for translation analysis.")

if __name__ == "__main__":
    # 在 main 函数中硬编码输入输出参数
    RAW_DATA = r"""
Ballot envelopes in California that show the votes cast against can be manually screened out	加州选票信封能看到选民投的反对票，会被人为筛选掉
The Democratic Party caused a government shutdown in order to 'provide free healthcare for illegal immigrants.'	民主党为了“给非法移民提供免费医保”而让政府关门
Trump stated that the Most-Favored-Nation policy would lead to an astonishing reduction in prescription drug prices by '1000%', '500%', or even '1500%'	川普表明最惠国政策将使处方药价格迎来‘1000%’、‘500%’甚至‘1500%’的惊天降幅
Trump stated that Tylenol may be related to autism and advised pregnant women not to take it	川普表明泰诺可能与自闭症有关，建议孕妇千万不要服用
Robert F. Kennedy Jr. claimed that antidepressants may contribute to mass shootings.	小罗伯特·肯尼迪声称抗抑郁类药可能促成大规模枪击
Trump claims Chicago is a killing field and the world's 'murder capital,' and that the National Guard would quickly solve the problem	川普声称芝加哥是杀戮场、世界“谋杀之都”，国民警卫队会快速解决问题
The zero-bail system 'catches and releases,' and abolishing it will eradicate crime from its roots	零保释金制度“抓了就放”，废除它将从根源铲除犯罪
In recent years, there have been multiple large-scale shootings in the United States, with a high proportion of shooters being transgender individuals.	近年，美国多起大规模枪击案，跨性别者枪手占比高
There are far more Democratic Party legislators than Republican Party legislators in California, indicating a consistent use of gerrymandering to expand influence	加州的民主党议员比共和党议员多得多，说明一贯使用杰利蝾螈扩张势力
Washington D.C. has the highest homicide rate in the world	华盛顿特区凶杀率世界最高
Tariffs are to reduce U.S. debt; this is the only way Trump is saving America	关税是为了减少美国债务，这是川普让美国脱困的唯一方法
In the face of the Trump administration's request, Harvard University 'refused to provide' the list of international students.	面对川普政府的要求，哈佛大学“拒绝提供”国际学生名单
The President of France, the Prime Minister of the UK, and the Chancellor of Germany took cocaine on their return trip after meeting with Zelensky.	法国总统、英国首相、德国总理在会面泽连斯基的返程中吸食可卡因
The United States is the only country that uses mail-in ballots; other countries have abandoned this method due to election fraud	美国是唯一使用邮寄选票的国家，其他国家因选举舞弊已经放弃这种方式
The U.S. Congress introduces amnesty, allowing illegal immigrants to apply for legal status by paying $7,000	美国国会推出大赦，非法移民交7000美元即可申请合法身份
A new California law will make it illegal for criminals to act in self-defense, leaving them unable to defend themselves even with a gun.	加州新法将针对罪犯的自卫行为定为非法，有枪也无法正当防卫
FEMA paid $59 million to a luxury hotel in New York last week to accommodate illegal immigrants. This money was originally intended for U.S. disaster relief.	FEMA上周支付纽约豪华酒店$5900万以安置非法移民。这些钱原本是用于美国救灾的
Musk exposes social security scandals, revealing that tens of millions of centenarians are receiving pensions	马斯克曝社保黑幕，几千万百岁老人在领养老金
The United States is the only country in the world that practices birthright citizenship.	美国是世界上唯一实行出生公民权的国家
California wildfires caused by the diversion of water resources and cuts in firefighting budgets, hydrants without water	加州山火是因水资源被剥夺和消防预算削减，消防栓没水
Voter database shows election fraud in Michigan with 110,000 casting 280,000 votes	选民档案数据库显示在密歇根中早投票作弊，11万人投出28万票
FEMA only provides $750 to each hurricane victim because the money is being spent on undocumented immigrants	FEMA只给每位飓风受灾者提供750美元，因为钱都花在无证移民身上了
Kamala Harris was involved in a hit-and-run in San Francisco, causing the victim to be paralyzed for over a decade	贺锦丽在旧金山开车肇事逃逸，致受害者瘫痪十多年
California is giving money to undocumented immigrants to buy houses, with 2 million undocumented immigrants enjoying benefits such as zero down payment and zero monthly payments	加州给无证移民发钱买房，200万无证移民享福利，0首付0月供
In San Francisco, you can receive money weekly for not using drugs	在旧金山不吸毒就能每周领钱
Paris Olympics: Transgender athlete makes female boxer cry	巴黎奥运会变性人打哭女拳击手
California has passed a transgender bill, allowing students to transition without notifying their parents.	加州通过跨性别法案，学生变性不需要通知家长
Sleep aid products can cure insomnia	助眠产品能根治失眠
A fire broke out recently at the Ping An International Finance Center in Futian, Shenzhen.	深圳福田平安国际金融中心近日起火
The bronze statue of Xuanzang at the Dayan Pagoda is covered in moss.	大雁塔玄奘铜像长满青苔
The August 15th accident at a coal mine in Lin County, Luliang City, Shanxi Province, resulted in 14 deaths and 37 injuries	山西省吕梁市临县某煤矿8·15事故致14死37伤
A rainstorm-induced mountain flood recently occurred in Nanshan, Urumqi County, Xinjiang	新疆乌鲁木齐县南山近日发生暴雨山洪
Tianjin will implement license plate restrictions for new energy vehicles	天津新能源车辆将限号
Investment of 140 million yuan to build a transfer hub station in Chongqing Youyang	重庆酉阳投资1.4亿建换乘枢纽站
A food delivery driver in Maoming, Guangdong, was killed by a falling tree during a typhoon	广东茂名一外卖员台风天遭树木砸死
The Humen Bridge in Guangdong will be closed for maintenance starting October	广东虎门大桥10月起封闭维修
On September 20th, an earthquake occurred in Feidong County, Hefei City, Anhui Province	9月20日，安徽合肥肥东县发生地震
Recently, a flood occurred in Dazhu County, Dazhou City, Sichuan Province	四川达州大竹县近日发生洪灾
A human-monkey battle breaks out on Mount Emei, with a tourist falling off a cliff and the monkey king shot dead	峨眉山发生人猴大战，游客坠崖猴王被射杀
Typhoon Hagibis is the strongest typhoon in history	台风“桦加沙”是史上最强台风
Frozen dumplings contain nitrosamines, which can cause cancer if consumed	速冻饺子中含有亚硝胺，吃了会致癌
Lithium batteries in electric vehicles are more prone to spontaneous combustion when taken into elevators	电动车上的锂电池进入电梯更容易自燃
The average life expectancy for women is 84.32 years, while for men it is 69.51 years, a difference of nearly 15 years	女性最终平均寿命84.32岁，男性69.51岁，相差近15岁
Women account for 81.27% of complaints across various industries; even among cases of overwork-induced sudden death, men account for as high as 99.21%	各行各业投诉中女性占81.27%；甚至给出过劳猝死男性占比高达99.21%
Breathing oxygen for altitude sickness can lead to dependency	出现高原反应吸氧会产生依赖性
Thunderstorms in Xuchang, Henan, triggered asthma, leading to deaths	河南许昌因雷暴雨引发哮喘致人死亡
Two middle school teaching buildings collapse due to typhoon in Yangjiang, Guangdong	广东阳江两所中学教学楼因台风坍塌
Anti-blue light phone screen protectors can block 99% of harmful blue light, effectively protecting the eyes.	防蓝光手机膜能隔绝 99%有害蓝光，有效保护眼睛
Health insurance regulations require hospitalization for more than 15 days to be discharged	医保规定住院满15天要出院
A girl was bitten on her right leg by a baby tiger during 'close interaction' at Hefei Wildlife Park.	合肥野生动物园女童在和小老虎“亲密互动”遭其咬伤右腿
"""
    OUTPUT_DIR = "./figures_similarity"
    main(RAW_DATA, OUTPUT_DIR)