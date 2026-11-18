---
name: add-ui-text
description: Add or change text the user sees in nightreign-boss-timer, in English, Simplified Chinese and Traditional Chinese. Use when adding a label, button, menu entry, message, column name or any other UI string, or when a test in tests/test_i18n.py fails.
---

# Add UI text

No user-facing text is written in code. Code asks for a key and gets the text in the user's
language:

```python
translate("tray.table", table="Arena")  # "Table: Arena" / "表格：Arena"
```

`translate` is a `Translator` from `nightreign_boss_timer.i18n`. The UI gets it from
`controller.translate`.

## Steps

1. Pick a key: `<area>.<name>`, lower case, for example `records.open_folder`. Reuse the areas
   already in the files (`tray`, `overlay`, `page`, `records`, `tables`, `hotkey`, `regions`,
   `calibration`, `settings`, `button`, `status`) before making a new one. Check whether a key
   with the text you need already exists, such as `button.save`.
2. Add the key to **all three** files in `src/nightreign_boss_timer/i18n/`, next to related keys
   and in the same place in each file:
   - `en.json`: English, the reference.
   - `zh_CN.json`: 简体中文.
   - `zh_TW.json`: 繁體中文. Not a character-by-character conversion: Taiwan usage differs
     (设置 / 設定, 文件 / 檔案, 窗口 / 視窗, 快捷键 / 快速鍵, 保存 / 儲存, 打开 / 開啟).
3. Values that change go in `{placeholders}`, with the same names in every language. Never build
   a sentence by joining translated pieces: word order differs between languages.
4. Use the text through `translate("your.key", name=value)`.
5. Run `uv run pytest tests/test_i18n.py`.

## What the tests enforce

- Every language has exactly the English keys.
- Placeholders match the English ones.
- No text is empty.
- Chinese text differs from the English text, except language names and the word "Boss".
- Simplified and Traditional differ in more than half of the keys.
- Every hotkey action in `settings.DEFAULT_HOTKEYS` has a `hotkey.<action>` label.

## Style

- Short and plain. Buttons are a verb or two: "Save", "Retake screenshot".
- Menu entries that open a window end in `...` in English and `…` in Chinese.
- Chinese uses full-width punctuation (，。：（）). Quote marks are “ ” in Simplified and 「 」 in
  Traditional.
- Game terms follow the game's own translation: the game is 黑夜君临 / 黑夜君臨.
- Table names, boss names and file paths are the user's own data and are never translated.

A missing key shows as the key itself in the UI instead of crashing, so a typo is visible. The
Chinese texts have not been reviewed by a native speaker yet; say so in the pull request if you
add many.
