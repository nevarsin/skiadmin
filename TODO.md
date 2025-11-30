# Roadmap

## 0.4.5 (Go Live Edition)
Features:
- Automatic 50% discount on Associates.membership_type on all articles except membership fees
Changes:
- Set Associates.card_sent on card sending functions
- Set auto insert minor membership card article 
- Autosend membership cards on trasactionsLines with membership cards in it

## 0.4.6
Features:
- Transactions: Confirmation modal before saving
- Transactions: Confirmation modal before sending receipt
- Associates: Confirmation modal before sending membership card
Bugfixes:
- Transaction: search stopped working (Associates does)

## 0.5.0
Features:
- New module: Skipass list (name TBD)
- Report: Skipass list for a specific day

# TODOs
## Refactoring
- Util functions all in one place
- Function naming consistency
- select2 being style consistant

## Subscriptions
- Have file upload more decent UI

## Associates
- Message when form Save is failing due to to field errors

## Transactions
- Find a better way to filter Membership Card article in signals.py
- Add email send confirmation (reporting email address)

# Bugfixes
## Associates
- /register test date picker behavior on mobile (no issues on Android FF/Chromium, iOS only?)
- Correct birth dates with years starting with 2xxx

## Subscriptions
- Do not show full attachment filename, it breaks layout. Just put a placeholder text


## Feature brain dump
- Skipass warehouse management (people who paid multiple passes in advance)
- Reports (skipass list, social competition list)
- Article management (with pricing and custom rule set, e.g. Same article attached to a minor would have a different price)
- How to add skipass to report (from either transaction list or the skipass warehouse)
- Configuration management (e.g. Title, background image)

