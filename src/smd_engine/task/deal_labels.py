"""Words of the deal fields on the task pages, English and Russian. The words
of the group pages stay in `labels.py`."""

from __future__ import annotations

from typing import Any

DEAL_LABELS: dict[str, dict[str, Any]] = {
    "en": {
        "positions": "Positions",
        "position": "Position",
        "audience": "For positions",
        "alpha_basis": (
            "Alpha is computed on {n} of {m} choice items: the shared core only; "
            "items for some positions and items of nature value or position are left out."
        ),
        "sha256": "sha256",
        "unit": "Unit",
        "claim": "Claim",
        "asserted_by": "Made by",
        "level": "Level",
        "levels": {"stated": "stated", "checked": "checked"},
        "source": "Source",
        "sources_for": "Sources for your answer",
        "red_line": "Red line",
        "if_reject": "If you reject",
        "if_reject_text": "Say in the reason which change you want. Counter-offers are made on the call.",
        "nature": "Nature",
        "natures": {
            "term": "term",
            "fact": "fact",
            "value": "value",
            "position": "position",
        },
        "after_reading": "Only after the reading of",
        "blocking_why": "a rejected red line always goes to the call",
        "source_ids": "Source ids",
        "pair": "Pair",
        "pair_open": "Open",
        "by_pair": "By pair",
        "call_by_pair": "Call points by pair",
        "view_note": (
            "View for {p}: part of the diff. Points for other positions, fact disputes "
            "over the buyer's claims (for the seller's side) and the other side's answers "
            "to value points are left out; a value point shows only open or settled."
        ),
        "agenda_view_note": (
            "Agenda for {p}: part of the agenda. Points for other positions, fact "
            "disputes over the buyer's claims (for the seller's side) and the other "
            "side's answers to value points are left out."
        ),
        "annex_point": "Annex point",
        "price_verdicts": {
            "met": "price: terms met - bargain at the in-person meeting",
            "not_met": "price: terms not met - bargain at the in-person meeting",
            "not_tested": "price: not tested - bargain at the in-person meeting",
        },
        "committed_by": "Committed by",
        "ledger": "Ledger head",
        "answers_withheld": (
            "The answers to this point are not on the agenda: it is for some "
            "positions or a value point. Each position has them in its view."
        ),
        "changed_since_run": "Commitment changed since the last run, not tested again",
        "sealed_side": {
            "floor": "the seller's floor",
            "ceiling": "the buyer's ceiling",
        },
        "sealed_what": "Sealed limit",
        "give": "How to give it",
        "sealed_how": (
            "No number is entered here. Give it with `smd deal seal` and put the "
            "commitment it prints in your answers file; the number stays with you "
            "and goes to the holder only for the comparison."
        ),
        "holder": "Holder",
        "stage": "Stage",
        "asking_price": "Asking price",
        "asking_opens": "Asking price: opens at stage {s}",
        "model_pass": "Model pass",
        "model_pass_allowed": "allowed: the parties consented",
        "model_pass_stopped": "not allowed: no consent of the parties",
        "choices": {
            "holds": "holds",
            "does_not_hold": "does not hold",
            "cannot_say": "cannot say",
            "accept": "accept",
            "reject": "reject",
        },
        "position_kinds": {
            "seller": "seller",
            "buyer": "buyer",
            "broker_sell": "sell-side broker",
            "broker_buy": "buy-side broker",
            "successor": "successor",
            "family": "family",
            "adviser": "adviser",
            "verifier": "verifier",
            "stakeholder": "stakeholder",
            "other": "other",
        },
    },
    "ru": {
        "positions": "Позиции",
        "position": "Позиция",
        "audience": "Для позиций",
        "alpha_basis": (
            "Альфа считается по {n} из {m} пунктов с выбором: только общее ядро; "
            "пункты для отдельных позиций и пункты по ценности или позиции не входят."
        ),
        "sha256": "sha256",
        "unit": "Единица",
        "claim": "Утверждение",
        "asserted_by": "Кто утверждает",
        "level": "Уровень",
        "levels": {"stated": "заявлено", "checked": "проверено"},
        "source": "Источник",
        "sources_for": "Источники для вашего ответа",
        "red_line": "Красная линия",
        "if_reject": "Если вы не принимаете",
        "if_reject_text": "В причине напишите, какое изменение нужно. Встречные предложения обсуждаются на созвоне.",
        "nature": "Природа пункта",
        "natures": {
            "term": "термин",
            "fact": "факт",
            "value": "ценность",
            "position": "позиция",
        },
        "after_reading": "Только после согласования прочтения пункта",
        "blocking_why": "непринятая красная линия всегда идёт на созвон",
        "source_ids": "Номера источников",
        "pair": "Пара",
        "pair_open": "Открыто",
        "by_pair": "По парам",
        "call_by_pair": "Точки для созвона по парам",
        "view_note": (
            "Вид для позиции «{p}»: часть сравнения. Пункты для других позиций, споры "
            "о фактах из утверждений покупателя (для стороны продавца) и ответы другой "
            "стороны по пунктам о ценности не показаны; пункт о ценности показан только "
            "как открытый или решённый."
        ),
        "agenda_view_note": (
            "Повестка для позиции «{p}»: часть повестки. Пункты для других позиций, "
            "споры о фактах из утверждений покупателя (для стороны продавца) и ответы "
            "другой стороны по пунктам о ценности не показаны."
        ),
        "annex_point": "Точка приложения",
        "price_verdicts": {
            "met": "цена: условия сошлись — торг на личной встрече",
            "not_met": "цена: условия не сошлись — торг на личной встрече",
            "not_tested": "цена: не проверено — торг на личной встрече",
        },
        "committed_by": "Дали обязательство",
        "ledger": "Голова журнала",
        "answers_withheld": (
            "Ответов по этой точке в повестке нет: она для части позиций или "
            "о стоимости. У каждой позиции они есть в её представлении."
        ),
        "changed_since_run": "Обязательство изменено после последней проверки, заново не проверено",
        "sealed_side": {
            "floor": "нижняя граница продавца",
            "ceiling": "верхняя граница покупателя",
        },
        "sealed_what": "Закрытая граница",
        "give": "Как дать",
        "sealed_how": (
            "Число здесь не вводится. Дайте его через `smd deal seal` и впишите "
            "выданное обязательство в файл ответов; число остаётся у вас и "
            "передаётся держателю только для сравнения."
        ),
        "holder": "Держатель",
        "stage": "Этап",
        "asking_price": "Запрашиваемая цена",
        "asking_opens": "Запрашиваемая цена: открывается на этапе {s}",
        "model_pass": "Проход модели",
        "model_pass_allowed": "разрешён: стороны согласны",
        "model_pass_stopped": "не разрешён: нет согласия сторон",
        "choices": {
            "holds": "верно",
            "does_not_hold": "неверно",
            "cannot_say": "не могу сказать",
            "accept": "принимаю",
            "reject": "не принимаю",
        },
        "position_kinds": {
            "seller": "продавец",
            "buyer": "покупатель",
            "broker_sell": "брокер продавца",
            "broker_buy": "брокер покупателя",
            "successor": "преемник",
            "family": "семья",
            "adviser": "советник",
            "verifier": "проверяющий",
            "stakeholder": "заинтересованная сторона",
            "other": "другая",
        },
    },
}
