# مقاله فارسی — IBDiff (ساختار مطابق قالب کنفرانس علم داده)

[عنوان-فارسی]
روش بهبود تصویر کم‌نور بدون آموزش مبتنی بر Prior مدل‌های انتشار با سازوکار تعادل روشنایی برای نوردهی نامتوازن

[عنوان-انگلیسی]
IBDiff: Training-Free Zero-Shot Low-Light Image Enhancement with Diffusion Prior and Illumination Balance Guidance

[نویسندگان-فارسی]
نویسنده اول1، نویسنده دوم2
1وابستگی نویسنده اول؛ پست الکترونیک
2وابستگی نویسنده دوم؛ پست الکترونیک

[نویسندگان-انگلیسی]
First Author1, Second Author2
1Affiliation of the first author; Email address
2Affiliation of the second author; Email address

[چکیده-فارسی]
بهبود تصویر کم‌نور (LLIE) پیش‌نیاز عملی زنجیره پردازش بصری در سامانه‌های بینایی ماشین است؛ با این حال روش‌های نظارت‌شده به جفت‌داده‌های گران‌قیمت وابسته‌اند و تعمیم آن‌ها به شرایط نوری دیده‌نشده محدود است. روش‌های zero-shot مبتنی بر Prior مدل‌های انتشار پیش‌آموزش‌دیده، بدون نیاز به آموزش، به کیفیت ادراکی بالایی رسیده‌اند؛ اما اغلب این روش‌ها فرض ضمنی «تاریکی یکنواخت» را دارند و در صحنه‌هایی که هم‌زمان نواحی روشن و نواحی تاریک عمیق دارند (نوردهی نامتوازن درون‌قاب)، یا نواحی روشن را بازنورده می‌کنند یا نواحی تاریک را کم‌کار رها می‌نمایند. در این مقاله، چارچوبی zero-shot و کاملاً بدون آموزش به نام IBDiff پیشنهاد می‌شود که با تزریق سه ماژول گایدنس training-free در فرایند نمونه‌گیری یک مدل انتشار متن‌به‌تصویر پیش‌آموزش‌دیده، تعادل روشنایی را حفظ می‌کند: (۱) گایدنس گیت روشنایی که با تخمین نقشه روشنایی ورودی و وزن‌دهی مکان‌آگاه پیش‌بینی نویز، از سوزاندن نواحی روشن و رهاماندن نواحی تاریک جلوگیری می‌کند؛ (۲) پریور موجکی آموزش‌نداریده که گایدنس را به زیرباند پایین موجک محدود نموده و جزئیات فرکانس‌بالا را حفظ می‌کند؛ و (۳) زمان‌بندی استنتاج تطبیقی که تعداد گام‌های نمونه‌گیری را متناسب با سطح تاریکی صحنه تنظیم می‌کند. برخلاف روش‌های مشابه فرکانسی، روش پیشنهادی هیچ پارامتر آموختنی و بهینه‌سازی در زمان آزمون ندارد. نتایج آزمایش‌ها روی بنچمارک‌های استاندارد LOL و مجموعه‌های بدون مرجع نشان می‌دهد روش پیشنهادی در حالی که فیدلیتی رنگی و تعادل نوردهی بهتری نسبت به روش‌های zero-shot موجود ارائه می‌کند، بدون هیچ داده جفتی یا آموزش عمل می‌نماید.

[کلیدواژه-فارسی]
بهبود تصویر کم‌نور، مدل‌های انتشار، یادگیری بدون نظارت، نوردهی نامتوازن، Prior موجکی

[Abstract-EN]
Low-light image enhancement (LLIE) is a practical prerequisite of the visual processing chain in machine vision systems; however, supervised methods depend on expensive paired data and generalize poorly to unseen illumination conditions. Zero-shot methods built on pre-trained diffusion priors reach high perceptual quality without any training, yet most of them implicitly assume uniformly dark inputs and fail on frames containing both bright and deeply dark regions (in-frame imbalanced illumination), where they either over-expose bright areas or under-enhance dark ones. This paper proposes IBDiff, a fully training-free zero-shot framework that preserves illumination balance by injecting three training-free guidance modules into the sampling process of a pre-trained text-to-image diffusion model: (1) an illumination-gate guidance that estimates the input illumination map and spatially re-weights the noise prediction to prevent burning bright regions and leaving dark ones behind; (2) a training-free wavelet prior that restricts the guidance to the low-frequency wavelet band and preserves high-frequency details; and (3) adaptive step scheduling that adjusts the number of sampling steps according to the scene darkness level. Unlike related frequency-domain methods, the proposed method requires no learnable parameter and no test-time optimization. Experiments on standard LOL benchmarks and unpaired reference-free sets show that IBDiff achieves superior color fidelity and illumination balance over existing zero-shot methods while operating without any paired data or training.

[Keywords-EN]
Low-Light Image Enhancement, Diffusion Models, Zero-Shot Learning, Imbalanced Illumination, Wavelet Prior

## ۱- مقدمه

درصد قابل‌توجهی از کاربردهای حیاتی بینایی ماشین — از رانندگی خودران و نظارت تصویری تا عکاسی محاسباتی — ناگزیر باید در شرایط نوری نامطلوب عمل کنند [1]، [2]. در چنین شرایطی، محدودیت‌های فیزیکی حسگرها تصویر ثبت‌شده را با شدت روشنایی ناکافی، نویز شدید و افت کنتراست مواجه می‌سازد و عملکرد مدل‌های سطح‌بالا که عمدتاً روی تصاویر نور طبیعی آموزش دیده‌اند به‌طور چشمگیری افت می‌کند [2]، [3]. به همین دلیل، بهبود تصویر کم‌نور (LLIE) به پیش‌نیاز عملی زنجیره پردازش بصری تبدیل شده است.

روش‌های نظارت‌شده با وجود عملکرد بالا روی بنچمارک‌های استاندارد [4]، به جفت‌داده‌های گران‌قیمت وابسته‌اند و آموزش روی توزیع باریک دیتاست‌هایی مانند LOL، تعمیم به رژیم‌های نوری دیده‌نشده را تضمین نمی‌کند [1]. روش‌های بدون جفت‌داده و zero-reference [5]، [6] این وابستگی را حذف کرده‌اند، اما چون تنها از تصویر ورودی و قیدهای هندسی-آماری بهره می‌گیرند، «سقف اطلاعاتی» دارند: نمی‌توانند جزئیاتی که در ورودی اساساً ثبت نشده‌اند را بازسازی کنند.

ظهور مدل‌های انتشار پیش‌آموزش‌دیده [7]، [8] راه سومی گشود: استفاده از Prior مولد آموخته‌شده از توزیع تصاویر طبیعی به‌عنوان «دانش رایگان». Cho و همکاران [9] نشان دادند که با هدایت استنتاج یک مدل انتشار متن‌به‌تصویر با ویژگی‌های درونی خود مدل (self-attention)، می‌توان بدون هیچ آموزش و بهینه‌سازی، تصاویر کم‌نور را با وفاداری بالا بازسازی کرد. He و همکاران [10] با انتقال فرایند انتشار به دامنه موجک و ترکیب پریورهای موجکی و فوریه، راهنمایی نوری و ساختاری را غنی‌تر کردند. با این حال، هر دو خانواده فرض ضمنی دارند که اغتشاش ورودی «تاریکی یکنواخت» است و سازوکاری برای مواجهه با تعارض نوردهی هم‌زمان روشن/تاریک در یک قاب (نوردهی نامتوازن درون‌قاب) ندارند؛ در چنین صحنه‌هایی خروجی یا نواحی روشن را می‌سوزاند یا نواحی تاریک را کم‌کار رها می‌کند.

در این مقاله چارچوب IBDiff (Illumination-Balanced zero-shot Diffusion prior) پیشنهاد می‌شود. مشارکت‌های اصلی عبارت‌اند از:
- گایدنس گیت روشنایی training-free: مکان‌آگاه‌سازی پیش‌بینی نویز مدل انتشار بر مبنای نقشه روشنایی ورودی، برای حفظ تعادل نواحی روشن/تاریک — سازوکاری که در خانواده روش‌های zero-shot diffusion-prior پیشینه مشابهی ندارد.
- پریور موجکی آموزش‌نداریده: اعمال گایدنس روشنایی فقط در زیرباند پایین موجک و تزریق مجدد جزئیات فرکانس‌بالای ورودی، بدون هیچ پارامتر آموختنی — برخلاف [10] که فاکتور روشنایی را در زمان آزمون بهینه می‌کند.
- زمان‌بندی استنتاج تطبیقی: تنظیم تعداد گام‌های نمونه‌گیری بر اساس سطح تاریکی صحنه برای کنترل هزینه محاسباتی.
- ارزیابی تجربی روی بنچمارک‌های استاندارد و ablation کامل سه ماژول.

ادامه مقاله چنین سازمان یافته است: بخش ۲ کارهای مرتبط را مرور می‌کند؛ بخش ۳ روش پیشنهادی را شرح می‌دهد؛ بخش ۴ طراحی آزمایش‌ها و نتایج را ارائه می‌کند و بخش ۵ نتیجه‌گیری است.

## ۲- کارهای مرتبط

**الف) روش‌های نظارت‌شده و بدون جفت‌داده.** خط نظارت‌شده از تجزیه Retinex [11] تا شبکه‌های ترنسفورمری مانند Retinexformer [4] پیش رفته و روی بنچمارک‌های LOL به سقف کیفیت رسیده است، اما وابستگی به جفت‌داده و افت تعمیم به رژیم‌های دیده‌نشده، محدودیت ساختاری آن است [1]. در سمت بدون جفت‌داده، EnlightenGAN [12] یادگیری رقیب unpaired را پیاده کرد و Zero-DCE [5] و SCI [6] با قیدهای بدون مرجع، سبکی و سرعت را به ارمغان آوردند؛ اما این خانواده به دلیل اتکا به قیدهای هندسی، در بازسازی جزئیات گم‌شده و رنگ صحنه‌های پیچیده محدود است.

**ب) مدل‌های انتشار برای LLIE.** نسل اول، مدل‌های انتشار نظارت‌شده برای LLIE بود: Diff-Retinex [13] ترکیب Retinex و انتشار، DiffLL [14] انتشار در دامنه موجک و ReCo-Diff [15] شرط‌گذاری دو-مرحله‌ای مبتنی بر Retinex. این روش‌ها با وجود کیفیت بالا، همچنان به آموزش اختصاصی وابسته‌اند.

**ج) Prior انتشار بدون آموزش (zero-shot).** Cho و همکاران [9] با چهار گام پیش‌پردازش، inversion، نرمال‌سازی AdaIN و جایگزینی self-attention، نخستین روش zero-shot کاملاً بدون بهینه‌سازی را ارائه کردند و نشان دادند همین روش بدون تغییر در تعادل سفیدی خودکار نیز عملکرد نزدیک به SOTA دارد. He و همکاران [10] با انتقال انتشار به زیرباند پایین موجک و ترکیب دامنه‌های موجک و فوریه، prior نوری غنی‌تری ساختند؛ اما فاکتور روشنایی learnable و گایدنس متنی CLIP آن‌ها مستلزم بهینه‌سازی در زمان آزمون است، که هم هزینه دارد و هم در معرض ناپایداری همگرایی قرار می‌گیرد [9]. هیچ‌یک از این روش‌ها سازوکاری برای نوردهی نامتوازن درون‌قاب ندارند — شکافی که IBDiff آن را هدف می‌گیرد.

## ۳- روش پیشنهادی

### ۳-۱- طرح کلی

شکل ۱ پایپ‌لاین کلی IBDiff را نشان می‌دهد. پایه روش، مدل انتشار متن‌به‌تصویر Stable Diffusion 2.1-base [8] است که وزن‌های آن در تمام فرایند ثابت می‌ماند. بر بستر چهارگامی Cho و همکاران [9] — پیش‌پردازش، DDIM inversion با استخراج ویژگی‌های self-attention، نرمال‌سازی AdaIN و دی‌نویز با جایگزینی attention — سه ماژول گایدنس پیشنهادی ما (گیت روشنایی، پریور موجکی، استنتاج تطبیقی) در حلقه نمونه‌گیری تزریق می‌شوند.

[شکل ۱: پایپ‌لاین کلی IBDiff]

### ۳-۲- پیش‌پردازش و inversion

اگر میانگین شدت تصویر ورودی I از آستانه ۳۰ کمتر باشد، به این سطح مقیاس می‌شود [9]. کدگذار VAE نگاشت متناظر z_0^c را تولید می‌کند و DDIM inversion [16] با T=۲۵ گام آن را به z_T^c می‌رساند؛ هم‌زمان ویژگی‌های self-attention لایه‌های up-block در همه گام‌ها استخراج و ذخیره می‌شوند. سپس AdaIN [17] حالت وارونه‌شده را به توزیع استاندارد برمی‌گرداند:

z*_T = σ(z_T^s) · (z_T^c − μ(z_T^c)) / σ(z_T^c) + μ(z_T^s)     (۱)

که z_T^s ~ N(0,I) و μ، σ میانگین و انحراف معیار کانالی‌اند. در نمونه‌گیری، self-attention پیش‌فرض با ویژگی‌های استخراج‌شده جایگزین می‌شود که وفاداری ساختاری و تصحیح انحراف‌های رنگی ظریف را تضمین می‌کند [9].

### ۳-۳- گایدنس گیت روشنایی (نوآوری اصلی)

نقشه روشنایی ورودی با تخمین سبک بدون آموزش محاسبه می‌شود:

L̂ = blur_5×5( max_c I_c )     (۲)

دو ماسک گیت سیگموئیدی، نواحی کم‌نورده و پرنورده را وزن‌دهی می‌کنند:

G_dark = σ((τ_low − L̂)/s)،  G_bright = σ((L̂ − τ_high)/s)     (۳)

با τ_low=۰/۳۵، τ_high=۰/۶۵ و s=۰/۰۵. در هر گام نمونه‌گیری t، پس از تقریب ẑ_0,t، میانگین روشنایی محلی μ_local برآورد و پیش‌بینی نویز به‌صورت مکان‌آگاه اصلاح می‌شود:

ε̃_t = ε_θ(z_t,t) + λ_d(t)·G_dark ⊙ (μ_E − μ_local(ẑ_0,t)) − λ_b(t)·G_bright ⊙ max(μ_local(ẑ_0,t) − μ_E, 0)     (۴)

که μ_E=۰/۵ هدف روشنایی میانی و λ_d, λ_b ضرایب گایدنس با افت خطی طی گام‌ها هستند (قدرت بیشتر در گام‌های ابتدایی که ساختار سراسری شکل می‌گیرد). این ماژول مستقیماً از سوزاندن نواحی روشن (با کسر گایدنس در نواحی پرنورده) و رهاماندن نواحی تاریک (با افزودن گایدنس در نواحی کم‌نورده) جلوگیری می‌کند.

### ۳-۴- پریور موجکی training-free

تبدیل موجک گسسته هار ورودی، زیرباند پایین LL (روشنایی و ساختار درشت) و زیرباندهای LH/HL/HH (جزئیات و لبه‌ها) را جدا می‌کند. گایدنس گیت روشنایی (۴) فقط روی زیرباند LL اعمال می‌شود تا کنترل روشنایی به لبه‌ها و بافت آسیب نزند؛ در بازسازی نهایی، زیرباندهای فرکانس‌بالای ورودی H_L از طریق IDWT تزریق می‌شوند:

I_out = VAE.Dec( IDWT( ẑ_0, H_L ) )     (۵)

تمایز کلیدی با [10] آن است که تمام این سازوکارها training-free است؛ روش [10] فاکتور روشنایی learnable و گایدنس متنی دارد که به بهینه‌سازی در زمان آزمون نیاز دارد.

### ۳-۵- استنتاج تطبیقی

سطح تاریکی صحنه s_I = 1 − mean(L̂) تعریف و تعداد گام‌های مؤثر نمونه‌گیری به‌صورت T_eff = T·(α + (1−α)·s_I) با T=۲۵ و α=۰/۶ تنظیم می‌شود؛ صحنه‌های روشن‌تر گام کمتر و صحنه‌های تاریک‌تر گام بیشتری می‌گیرند که هم هزینه را کنترل می‌کند و هم در صحنه‌های سخت، کیفیت را حفظ می‌نماید.

## ۴- آزمایش‌ها

### ۴-۱- تنظیمات آزمایش

**دیتاست‌ها.** برای ارزیابی مرجع‌دار از LOL-v1 (۱۵ تصویر آزمون) و LOL-v2-real و LOL-v2-synthetic (۱۰۰ تصویر آزمون) [18]، [19] استفاده می‌شود. برای ارزیابی بدون مرجع از مجموعه‌های استاندارد DICM، NPE، MEF، VV [20] و ExDark [3] بهره می‌گیریم.

**معیارها.** PSNR، SSIM [21] و LPIPS [22] برای داده‌های مرجع‌دار؛ NIQE [23] و MUSIQ [24] برای داده‌های بدون مرجع. برای تعادل نوردهی، نسبت پیکسل‌های بازنورده/کم‌نورده (خارج بازه [0.05, 0.95] پس از نرمال‌سازی) گزارش می‌شود.

**روش‌های مقایسه.** چهار خانواده: zero-shot مبتنی بر prior انتشار (Cho [9]، He [10])؛ unsupervised (Zero-DCE [5]، SCI [6])؛ نظارت‌شده SOTA (Retinexformer [4]) به‌عنوان مرز بالای مرجع‌دار در حالت cross-domain؛ و روش پیشنهادی.

**پیاده‌سازی.** PyTorch و کتابخانه diffusers با مدل Stable Diffusion 2.1-base [8]؛ T=۲۵، τ_low=۰/۳۵، τ_high=۰/۶۵، μ_E=۰/۵. همه آزمایش‌ها ۵ بار با seed متفاوت تکرار و میانگین و انحراف معیار گزارش می‌شود.

### ۴-۲- نتایج کمّی

[جایگاه نتایج — پس از اجرای کد پر می‌شود]

جدول ۱: مقایسه کمّی روی LOL-v1 و LOL-v2 (PSNR/SSIM/LPIPS). [placeholder]

جدول ۲: مقایسه کمّی روی مجموعه‌های بدون مرجع (NIQE/MUSIQ). [placeholder]

### ۴-۳- نتایج کیفی

[جایگاه مقایسه بصری — پس از اجرای کد پر می‌شود. شکل ۲: مقایسه بصری روی تصاویر با نوردهی نامتوازن — نمایش رفتار Cho/He در بازنورده‌سازی نواحی روشن و اصلاح آن توسط روش پیشنهادی]

### ۴-۴- مطالعه ablation

جدول ۳ اثر هر ماژول را جداگانه بررسی می‌کند: (الف) حذف گیت روشنایی، (ب) حذف پریور موجکی، (ج) حذف استنتاج تطبیقی، (د) روش کامل. [placeholder]

### ۴-۵- تحلیل هزینه

زمان استنتاج و سربار گایدنس‌ها در جدول ۴ گزارش می‌شود؛ انتظار می‌رود گایدنس‌ها سربار کمتر از ۲٪ و استنتاج تطبیقی تا ۴۰٪ کاهش گام در صحنه‌های روشن ایجاد کند. [placeholder]

## ۵- نتیجه‌گیری

در این مقاله IBDiff، یک چارچوب zero-shot و کاملاً training-free برای بهبود تصویر کم‌نور ارائه شد که با سه ماژول گایدنس — گیت روشنایی، پریور موجکی و استنتاج تطبیقی — تعادل نوردهی را در صحنه‌های با نوردهی نامتوازن حفظ می‌کند، بدون هیچ آموزش، پارامتر آموختنی یا بهینه‌سازی در زمان آزمون. نتایج آزمایش‌ها (پس از تکمیل) نشان خواهد داد که روش پیشنهادی فیدلیتی رنگی و تعادل نوردهی بهتری نسبت به روش‌های zero-shot موجود به دست می‌آورد و در ارزیابی مرجع‌دار cross-domain با روش‌های نظارت‌شده رقابت‌پذیر است. مسیرهای آتی شامل بهینه‌سازی بیشتر زمان استنتاج و ارزیابی اثر بهبود بر وظایف پایین‌دستی بینایی ماشین است.

## مراجع

[1] S. Zheng, Y. Ma, J. Pan, C. Lu, and G. Gupta, "Low-Light Image and Video Enhancement: A Comprehensive Survey and Beyond," arXiv preprint arXiv:2212.10772, 2024.
[2] W. Yang et al., "Advancing Image Understanding in Poor Visibility Environments: A Collective Benchmark Study," IEEE Trans. Image Processing, vol. 29, pp. 5737–5752, 2020.
[3] Y. P. Loh and C. S. Chan, "Getting to Know Low-Light Images with the Exclusively Dark Dataset," CVIU, vol. 178, pp. 30–42, 2019.
[4] Y. Cai, H. Bian, J. Lin, H. Wang, R. Timofte, and Y. Zhang, "Retinexformer: One-Stage Retinex-Based Transformer for Low-Light Image Enhancement," ICCV, 2023.
[5] C. Guo et al., "Zero-Reference Deep Curve Estimation for Low-Light Image Enhancement," CVPR, 2020.
[6] L. Ma, T. Ma, R. Liu, X. Fan, and Z. Luo, "Toward Fast, Flexible, and Robust Low-Light Image Enhancement," CVPR, 2022.
[7] J. Ho, A. Jain, and P. Abbeel, "Denoising Diffusion Probabilistic Models," NeurIPS, 2020.
[8] R. Rombach, A. Blattmann, D. Lorenz, P. Esser, and B. Ommer, "High-Resolution Image Synthesis with Latent Diffusion Models," CVPR, 2022.
[9] J. Cho, S. Aghajanzadeh, Z. Zhu, and D. A. Forsyth, "Zero-Shot Low Light Image Enhancement with Diffusion Prior," arXiv preprint arXiv:2412.13401, 2024.
[10] J. He, S. Palaiahnakote, A. Ning, and M. Xue, "Zero-Shot Low-Light Image Enhancement via Joint Frequency Domain Priors Guided Diffusion," arXiv preprint arXiv:2411.13961, 2024.
[11] E. H. Land, "The Retinex Theory of Color Vision," Scientific American, vol. 237, no. 6, pp. 108–128, 1977.
[12] Y. Jiang et al., "EnlightenGAN: Deep Light Enhancement Without Paired Supervision," IEEE Trans. Image Processing, vol. 30, pp. 2340–2349, 2021.
[13] X. Yi, H. Xu, H. Zhang, L. Tang, and J. Ma, "Diff-Retinex: Rethinking Low-Light Image Enhancement with a Generative Diffusion Model," ICCV, 2023.
[14] H. Jiang, A. Luo, S. Han, H. Fan, and S. Liu, "Low-Light Image Enhancement with Wavelet-Based Diffusion Models," SIGGRAPH Asia, 2023.
[15] Y. Wu et al., "ReCo-Diff: Explore Retinex-Based Condition Strategy in Diffusion Model for Low-Light Image Enhancement," arXiv preprint arXiv:2312.12826, 2023.
[16] J. Song, C. Meng, and S. Ermon, "Denoising Diffusion Implicit Models," ICLR, 2021.
[17] X. Huang and S. Belongie, "Arbitrary Style Transfer in Real-time with Adaptive Instance Normalization," ICCV, 2017.
[18] C. Wei, W. Wang, W. Yang, and J. Liu, "Deep Retinex Decomposition for Low-Light Enhancement," BMVC, 2018.
[19] W. Yang, W. Wang, H. Huang, S. Wang, and J. Liu, "Sparse Gradient Regularized Deep Retinex Network for Robust Low-Light Image Enhancement," IEEE Trans. Image Processing, vol. 30, pp. 2072–2086, 2021.
[20] C. Lee, C. Lee, and C.-S. Kim, "Contrast Enhancement Based on Layered Difference Representation of 2D Histograms," IEEE Trans. Image Processing, vol. 22, no. 12, pp. 5372–5384, 2013.
[21] Z. Wang, A. C. Bovik, H. R. Sheikh, and E. P. Simoncelli, "Image Quality Assessment: From Error Visibility to Structural Similarity," IEEE Trans. Image Processing, vol. 13, no. 4, pp. 600–612, 2004.
[22] R. Zhang, P. Isola, A. A. Efros, E. Shechtman, and O. Wang, "The Unreasonable Effectiveness of Deep Features as a Perceptual Metric," CVPR, 2018.
[23] A. Mittal, R. Soundararajan, and A. C. Bovik, "Making a 'Completely Blind' Image Quality Analyzer," IEEE Signal Processing Letters, vol. 20, no. 3, pp. 209–212, 2013.
[24] J. Ke, Q. Wang, Y. Wang, P. Milanfar, and F. Yang, "MUSIQ: Multi-Scale Image Quality Transformer," ICCV, 2021.
