from sqlalchemy import select, union
from typing import List


from bill.db import db, Bill, PartyUser


def get_bill_by_uid(uid) -> List[Bill]:
    payer_bill = select(Bill).join(
        PartyUser,
        (Bill.party_id == PartyUser.party_id) & (PartyUser.uid == uid)
    )
    payee_bill = select(Bill).join(
        PartyUser,
        (Bill.counterparty_id == PartyUser.party_id) & (PartyUser.uid == uid)
    )
    query = union(payer_bill, payee_bill)
    return db.session.execute(query).all()
