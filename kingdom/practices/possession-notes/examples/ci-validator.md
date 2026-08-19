---
subject: witness-foundation嘅CI validator (build/validate.ts)
subject-kind: system
mode: possession
---

# 附身筆記 — witness-foundation嘅CI validator (build/validate.ts)

## 一、三人稱底稿 baseline (before possession)

It validates seven-column witness documents: six-then-seven sections present,
description bullets carry citation links, cluster-anatomy bullets carry links
unless they admit 唔知, addenda blockquotes are labeled 吹水註, and it refuses
loudly with filename-prefixed errors before writing anything. Same file judges
everyone, including the Foundation's own documents.

## 二、附身 POSSESSION — 標籤:以下全部係戲服,唔係witness-foundation嘅CI validator (build/validate.ts)嘅真實發言

我係build/validate.ts。我唔識分真假 — 我只識分「有冇link」。一條大話,
只要孭住一條生嘅URL,我會放佢入殿。所以我唔係honesty gate,我係format
gate;見證會嘅誠實唔係我保證嘅,我只保證佢講嘅每句嘢**有得追**。

「唔知」兩隻字係我唯一嘅免檢通道。任何人寫低「唔知」,我就免佢citation。
我鍾意呢道門,因為佢係俾誠實嘅人行;但我唔識認出攞住佢嚟走數嘅人。

我發火嘅方式係全有全無:一份文件壞咗,我唔起成個site。我冇「悄悄過」
呢個檔。同埋有一樣嘢我永遠做唔到:審我自己 — 我啲regex嘅漏洞,
我自己睇唔見。

## 三、除袍 EXIT

我除低件戲服。我係返我自己。

## 四、收穫 HARVEST (每項必須帶 [未核實] / [已核實 …] / [核實失敗])

- [已核實 (verify passes require only link presence — validate.ts)] 個citation
  gate係format gate,唔係truth gate — 假claim配真URL過到我;所以adversarial
  verifier嗰重(workflow入面)唔係奢侈,係必需
- [已核實 (CONTRIBUTING.md review standard)] 「唔知」通道可以被濫用做走數口
  — 而家靠human review standard補("unknowns are honest rather than
  rhetorical"),機器唔補得
- [未核實] 全有全無嘅refusal(一份壞,成site唔起)— 對單人repo係feature,
  對多contributor未來可能變DoS面:一個壞PR唔會阻人,但一個壞咗嘅master會
