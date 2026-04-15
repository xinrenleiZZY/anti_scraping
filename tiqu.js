function extractAllProductInfo(product) {
    // 1. 判断广告类型
    let adType = 'organic';
    const hasSponsored = product.querySelector('.puis-sponsored-label-text') !== null;
    const isBrandAd = product.querySelector('[cel_widget_id*="sb-themed-collection"]') !== null;
    const isVideoAd = product.querySelector('video, [data-component-type="s-video"]') !== null;
    
    if (isVideoAd) adType = 'SB_Video';
    else if (isBrandAd) adType = 'SB';
    else if (hasSponsored) adType = 'SP';
    
    // 2. 提取信息
    const info = {
        // 广告类型
        adType: adType,
        isSponsored: hasSponsored,
        
        // 基础信息
        asin: product.getAttribute('data-asin'),
        url: product.querySelector('h2 a, a[aria-label*="Sponsored"]')?.getAttribute('href'),
        title: product.querySelector('h2 span, .a-size-base-plus')?.innerText?.trim(),
        
        // 图片
        image_small: product.querySelector('.s-image')?.getAttribute('src'),
        image_large: product.querySelector('.s-image')?.getAttribute('src')?.replace('_UL320_', '_SL1500_'),
        
        // 价格
        price_current: product.querySelector('.a-price .a-offscreen')?.innerText,
        price_list: product.querySelector('.a-text-strike')?.innerText,
        price_unit: product.querySelector('.a-price[data-a-size="b"] .a-offscreen')?.innerText,
        
        // 评分
        rating_stars: product.querySelector('.a-icon-star-mini .a-icon-alt')?.innerText,
        rating_count: product.querySelector('[aria-label*="rating"]')?.getAttribute('aria-label'),
        
        // 属性
        spec: product.querySelector('.s-background-color-platinum')?.innerText,
        variation: product.querySelector('.s-variation-options-link')?.innerText,
        
        // 销售
        sales: product.querySelector('[aria-label*="bought in past month"]')?.innerText,
        
        // 优惠
        coupon: product.querySelector('.s-coupon-highlight-color')?.innerText,
        
        // 配送
        delivery_primary: product.querySelector('.udm-primary-delivery-message')?.innerText,
        delivery_secondary: product.querySelector('.udm-secondary-delivery-message')?.innerText,
        
        // 标识
        isPrime: !!product.querySelector('.a-icon-prime'),
        isAmazonFulfilled: product.innerText.includes('Ships from Amazon'),
    };
    
    // 3. 如果是SB广告，提取内部商品
    if (adType === 'SB') {
        info.innerProducts = [];
        product.querySelectorAll('[data-asin][data-asin!=""]').forEach(inner => {
            info.innerProducts.push({
                asin: inner.getAttribute('data-asin'),
                title: inner.querySelector('.a-size-base-plus, .a-truncate-full')?.innerText,
                price: inner.querySelector('.a-price .a-offscreen')?.innerText,
                rating: inner.querySelector('.a-icon-star-mini .a-icon-alt')?.innerText,
                url: inner.closest('a')?.getAttribute('href'),
            });
        });
    }
    
    return info;
}

// 使用
const allProducts = document.querySelectorAll('[data-component-type="s-search-result"], .s-result-item[data-asin=""]');
const results = Array.from(allProducts).map(extractAllProductInfo);
console.table(results);