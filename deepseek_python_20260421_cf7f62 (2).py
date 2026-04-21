import re
import json
from playwright.sync_api import sync_playwright

def extract_google_form_data(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(2000)
            html_content = page.content()
            pattern = r'var\s+FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\]);'
            match = re.search(pattern, html_content, re.DOTALL)
            if not match:
                raise ValueError("Could not find FB_PUBLIC_LOAD_DATA_ in page source.")
            data = json.loads(match.group(1))
            form_info = data[1] if len(data) > 1 else None
            if not form_info:
                raise ValueError("Invalid form data structure")
            title = "Untitled Form"
            if len(form_info) > 8 and form_info[8]:
                title = form_info[8]
            elif len(form_info) > 1 and isinstance(form_info[1], list) and len(form_info[1]) > 0:
                title = form_info[1][0] if isinstance(form_info[1][0], str) else "Untitled Form"
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
                            question_data = parse_question_item(item)
                            if question_data:
                                questions.append(question_data)
            if not questions:
                questions = parse_alternative(data)
            if not questions:
                raise ValueError("No questions found in the form.")
            return {
                'title': title.strip(),
                'reading_passage': reading_passage.strip(),
                'questions': questions
            }
        finally:
            browser.close()

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
    correct_answer_index = -1
    if len(item) > 4 and isinstance(item[4], list):
        options_data = item[4]
        for opt in options_data:
            if isinstance(opt, list) and len(opt) > 0:
                opt_text = opt[0] if len(opt) > 0 and isinstance(opt[0], str) else ""
                if not opt_text and len(opt) > 1 and isinstance(opt[1], str):
                    opt_text = opt[1]
                if opt_text:
                    options.append(opt_text)
            elif isinstance(opt, str):
                options.append(opt)
    if len(item) > 8 and isinstance(item[8], list):
        correct_data = item[8]
        if len(correct_data) > 0:
            if isinstance(correct_data[0], (int, float)):
                correct_answer_index = int(correct_data[0])
            elif isinstance(correct_data[0], list) and len(correct_data[0]) > 0:
                correct_answer_index = int(correct_data[0][0]) if isinstance(correct_data[0][0], (int, float)) else -1
    if correct_answer_index == -1 and len(item) > 9 and isinstance(item[9], list):
        if len(item[9]) > 0 and isinstance(item[9][0], (int, float)):
            correct_answer_index = int(item[9][0])
    if correct_answer_index < 0 or correct_answer_index >= len(options):
        correct_answer_index = 0
    if not options:
        return None
    return {
        'text': question_text.strip(),
        'options': options,
        'correct_answer_index': correct_answer_index
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
                        question_text = ""
                        for elem in item:
                            if isinstance(elem, str) and len(elem) > 10 and "?" in elem:
                                question_text = elem
                                break
                        options = []
                        correct_idx = -1
                        for idx, elem in enumerate(item):
                            if isinstance(elem, list) and len(elem) > 0:
                                for opt in elem:
                                    if isinstance(opt, str) and len(opt) > 0 and opt not in options:
                                        options.append(opt)
                                if idx + 1 < len(item) and isinstance(item[idx + 1], list):
                                    corr = item[idx + 1]
                                    if len(corr) > 0 and isinstance(corr[0], (int, float)):
                                        correct_idx = int(corr[0])
                        if question_text and options and correct_idx >= 0:
                            questions.append({
                                'text': question_text.strip(),
                                'options': options,
                                'correct_answer_index': correct_idx
                            })
                traverse(item, depth + 1)
        elif isinstance(obj, dict):
            for value in obj.values():
                traverse(value, depth + 1)
    traverse(data)
    return questions