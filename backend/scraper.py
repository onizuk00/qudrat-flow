import re
import json
from playwright.async_api import async_playwright

async def extract_google_form_data(url: str):
    """
    استخراج بيانات Google Form بأقصى سرعة.
    - حظر الموارد غير الضرورية
    - استخدام domcontentloaded
    - مهلة 30 ثانية
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-gpu',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--blink-settings=imagesEnabled=false',
                '--disable-javascript',   # قد يعطل بعض النماذج، جرب بدونه إذا لزم الأمر
            ]
        )
        context = await browser.new_context(
            viewport={'width': 800, 'height': 600},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        # حظر الصور والخطوط وملفات CSS
        async def block_resources(route):
            if route.request.resource_type in ['image', 'stylesheet', 'font', 'media']:
                await route.abort()
            else:
                await route.continue_()
        await page.route('**/*', block_resources)

        try:
            # استخدم 'domcontentloaded' بدلاً من 'networkidle' للسرعة
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            # انتظار قصير جداً (500ms) للجافاسكريبت الأساسي
            await page.wait_for_timeout(500)

            html = await page.content()
            match = re.search(r'var\s+FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\]);', html, re.DOTALL)
            if not match:
                # محاولة بديلة بانتظار أطول قليلاً
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(1000)
                html = await page.content()
                match = re.search(r'var\s+FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\]);', html, re.DOTALL)
                if not match:
                    raise ValueError("لم نجد بيانات النموذج. تأكد من أن الرابط صحيح ونموذج اختبار.")

            data = json.loads(match.group(1))
            form_info = data[1] if len(data) > 1 else None
            if not form_info:
                raise ValueError("بنية النموذج غير صالحة")

            # استخراج العنوان
            title = "نموذج بدون عنوان"
            if len(form_info) > 8 and form_info[8]:
                title = form_info[8]
            elif len(form_info) > 1 and isinstance(form_info[1], list) and len(form_info[1]) > 0:
                title = form_info[1][0] if isinstance(form_info[1][0], str) else "نموذج بدون عنوان"

            # نص القراءة (إن وجد)
            reading_passage = ""
            if len(form_info) > 10 and isinstance(form_info[10], str):
                reading_passage = form_info[10]

            questions = []
            if len(form_info) > 1 and isinstance(form_info[1], list):
                sections = form_info[1]
                for section in sections:
                    if isinstance(section, list) and len(section) > 1:
                        items = section[1] if len(section) > 1 else []
                        for item in items:
                            q = parse_question_item(item)
                            if q:
                                questions.append(q)

            if not questions:
                questions = parse_alternative(data)

            if not questions:
                raise ValueError("لم يتم العثور على أسئلة في النموذج")

            return {
                'title': title.strip(),
                'reading_passage': reading_passage.strip(),
                'questions': questions
            }
        finally:
            await browser.close()

def parse_question_item(item):
    if not isinstance(item, list) or len(item) < 4:
        return None
    question_text = ""
    if len(item) > 2 and isinstance(item[2], str):
        question_text = item[2]
    elif len(item) > 1 and isinstance(item[1], str):
        question_text = item[1]
    if not question_text:
        return None

    options = []
    if len(item) > 4 and isinstance(item[4], list):
        for opt in item[4]:
            if isinstance(opt, list) and len(opt) > 0:
                opt_text = opt[0] if isinstance(opt[0], str) else ""
                if not opt_text and len(opt) > 1 and isinstance(opt[1], str):
                    opt_text = opt[1]
                if opt_text:
                    options.append(opt_text)
            elif isinstance(opt, str):
                options.append(opt)

    correct_index = -1
    if len(item) > 8 and isinstance(item[8], list) and len(item[8]) > 0:
        if isinstance(item[8][0], (int, float)):
            correct_index = int(item[8][0])
        elif isinstance(item[8][0], list) and len(item[8][0]) > 0 and isinstance(item[8][0][0], (int, float)):
            correct_index = int(item[8][0][0])
    if correct_index == -1 and len(item) > 9 and isinstance(item[9], list) and len(item[9]) > 0:
        if isinstance(item[9][0], (int, float)):
            correct_index = int(item[9][0])

    if correct_index < 0 or correct_index >= len(options):
        correct_index = 0
    if not options:
        return None
    return {
        'text': question_text.strip(),
        'options': options,
        'correct_answer_index': correct_index
    }

def parse_alternative(data):
    questions = []
    def traverse(obj, depth=0):
        if depth > 10:
            return
        if isinstance(obj, list):
            for item in obj:
                if isinstance(item, list) and len(item) >= 3:
                    has_options = any(isinstance(x, list) and len(x) > 0 and isinstance(x[0], str) for x in item)
                    has_text = any(isinstance(x, str) and len(x) > 10 for x in item)
                    if has_options and has_text:
                        q_text = ""
                        for elem in item:
                            if isinstance(elem, str) and len(elem) > 10 and "?" in elem:
                                q_text = elem
                                break
                        opts = []
                        correct_idx = -1
                        for idx, elem in enumerate(item):
                            if isinstance(elem, list) and len(elem) > 0:
                                for opt in elem:
                                    if isinstance(opt, str) and opt not in opts:
                                        opts.append(opt)
                                if idx+1 < len(item) and isinstance(item[idx+1], list) and len(item[idx+1]) > 0:
                                    if isinstance(item[idx+1][0], (int, float)):
                                        correct_idx = int(item[idx+1][0])
                        if q_text and opts and correct_idx >= 0:
                            questions.append({
                                'text': q_text.strip(),
                                'options': opts,
                                'correct_answer_index': correct_idx
                            })
                traverse(item, depth+1)
        elif isinstance(obj, dict):
            for val in obj.values():
                traverse(val, depth+1)
    traverse(data)
    return questions
