#!/usr/bin/env python3
"""プライバシーポリシーの問い合わせ先を記入する（日本語版・英語版の両方）。

  python3 scripts/set_contact.py kateisaien.note@gmail.com
  python3 scripts/set_contact.py "https://forms.gle/xxxxx"   # フォームのURLでもよい

★なぜ必要か
  AdSenseの審査では「運営者に連絡する手段があること」が見られる。
  2026-10-02時点で privacy.html / en/privacy.html の両方が
  「（ここに問い合わせ先を記入してください）」のまま公開されていた。
★メールアドレスは mailto: のリンクにする。URLならそのままリンクにする。
"""
import io, re, sys

if len(sys.argv) != 2:
    sys.exit(__doc__)
v = sys.argv[1].strip()
is_url = v.startswith("http")
href = v if is_url else "mailto:" + v

# ★URLはそのまま出すと長くて読みにくいので、日本語版・英語版それぞれの言葉にする
TARGETS = [
    ("privacy.html", "（ここに問い合わせ先を記入してください）", "お問い合わせフォーム"),
    ("en/privacy.html", "(add your contact address here)", "Contact form"),
]
for f, placeholder, label in TARGETS:
    link = f'<a href="{href}" target="_blank" rel="noopener">{label if is_url else v}</a>' 
    s = io.open(f, encoding="utf-8").read()
    if placeholder in s:
        s = s.replace(placeholder, link)
    else:
        # 2回目以降（すでに記入済み）は中身だけ差し替える
        s = re.sub(r'(お問い合わせ：|Contact: )<strong>.*?</strong>',
                   lambda m: m.group(1) + f"<strong>{link}</strong>", s, count=1)
    io.open(f, "w", encoding="utf-8").write(s)
    print("記入:", f)
print("\n次: git add -A && git commit && git push で公開（デプロイは自動）")
