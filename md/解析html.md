你帮我继续，我还不知道怎么定位的，首先，这是商品首页：class="sg-col-20-of-24 s-matching-dir sg-col-16-of-20 sg-col sg-col-8-of-12 sg-col-12-of-16"，首页是个div，然后接着在一个span里面，然后在一个div里面（class = s-main-slot s-result-list s-search-results sg-row），里面有很多并列的div，有的是商品，有的是区块标题


amazon关键词页面HTML解析（人工解析，可能会有偏差）：

class="s-main-slot s-result-list s-search-results sg-row"
    <div>广告</div>
    <div>标题</div>
    <div>商品</div>
    <div>标题</div>
    <div>商品</div>
    <script>无用标签</script>
    <link>无用link标签
    ......
    <div></div>


.s-main-slot.s-result-list.s-search-results.sg-row (商品列表容器)
│
├── 区块标题 (如 "Results")
│   └── <div class="s-result-item s-widget...">  ← 不是商品
│
├── 广告 (品牌展示广告(顶部有一个))
│   └── <div class="s-result-item s-widget s-widget-spacing-large AdHolder s-flex-full-width" data-asin="">  ← data-asin为空
│       └── 内部包含多个商品 (如 Tens Towels 的3个产品)
│

├── 广告 (品牌展示广告)
│   └── <div class="s-result-item s-widget AdHolder" data-asin="">  ← data-asin为空
│       └── 内部包含多个商品 (如 Tens Towels 的3个产品)
│
├── 赞助商品 (单个广告)
│   └── <div role="listitem" data-asin="B0GMY978L7" data-component-type="s-search-result" class="... AdHolder">
│
├── 自然搜索结果
│   └── <div role="listitem" data-asin="B0XXXXXXXX" data-component-type="s-search-result">
│
└── 更多商品...