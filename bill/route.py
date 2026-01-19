from flask import Blueprint, g, make_response, request, jsonify, abort
from decimal import Decimal
from typing import Dict, List
from random import choice
from sqlalchemy import select


from common.auth import require_auth, with_logto_token
from common.util import (
    get_user_by_id,
    get_organizations_by_uid,
    get_organizations_member_by_id
)
from bill.db import (
    db,
    Bill, BillAmount,
    ApportionMethod, Apportion, ApportionDetail, ApportionPreset, ApportionPresetDetail,
    Party, PartyUser
)
from bill.util import get_bill_by_uid
from bill.validate import ValidatedBill


bill = Blueprint('bill', __name__, url_prefix="/bill")


@bill.route("/list", methods=['GET'])
@require_auth
@with_logto_token
def bill_list():
    uid = g.current_user["sub"]
    bill_list = get_bill_by_uid(uid)
    if len(bill_list) == 0:
        return make_response('', 204)
    
    result = []
    for bid in [b.id for b in bill_list]:
        stmt = select(Bill).where(Bill.id == bid)
        bill = db.session.execute(stmt).scalar_one()
        if bill.deleted is True:
            continue
        
        amount_stmt = select(BillAmount).where(
            BillAmount.uid == uid,
            BillAmount.bill_id == bid
        )
        amount = db.session.execute(amount_stmt).scalar_one()
        
        payer_stmt = select(PartyUser).where(PartyUser.party_id == bill.party_id)
        payer_party_user = db.session.execute(payer_stmt).scalar_one_or_none()
        
        result.append({
            "id": bid,
            "title": bill.title,
            "time": bill.trade_time.isoformat(),
            "description": bill.description,
            "total": bill.price,
            "payer": get_user_by_id(payer_party_user.uid)["username"],
            "amount": {
                "price": amount.price,
                "diff": amount.diff
            },
            "is_completed": amount.completed
        })

    return jsonify(result)


@bill.route("/complete_amount", methods=['POST'])
@require_auth
def complete_amount():
    uid = g.current_user["sub"]
    bid = request.get_json().get("bill_id")
    if bid is None:
        abort(400)
    
    stmt = select(BillAmount).where(
        BillAmount.uid == uid,
        BillAmount.bill_id == bid
    )
    amount = db.session.execute(stmt).scalar_one()
    amount.completed = True
    db.session.commit()
    db.session.flush()
    
    stmt = select(Bill).where(Bill.id == bid)
    bill = db.session.execute(stmt).scalar_one()
    
    stmt = select(PartyUser).where(PartyUser.party_id == bill.party_id)
    payer = db.session.execute(stmt).scalar_one()
    
    stmt = select(BillAmount).where(BillAmount.bill_id == bid)
    all_amounts = db.session.execute(stmt).scalars().all()
    
    # Check if all other users (excpet payer) have completed their parts
    if all(
        bill_amount.completed 
        for bill_amount in all_amounts 
        if bill_amount.uid != payer.uid
    ):
        stmt = select(BillAmount).where(
            BillAmount.bill_id == bid,
            BillAmount.uid == payer.uid
        )
        payer_amount: BillAmount = db.session.execute(stmt).scalar_one()
        payer_amount.completed = True
        db.session.commit()
    
    return make_response('', 200)


@bill.route("/delete_amount", methods=['POST'])
@require_auth
def delete_bill():
    uid = g.current_user["sub"]
    data = request.get_json()
    bid = data.get("bill_id")
    if bid is None:
        abort(400)
    
    stmt = select(Bill).where(Bill.id == bid)
    bill = db.session.execute(stmt).scalar_one()
    bill.deleted = True
    db.session.commit()
    return make_response('', 200)


@bill.route("/apportion_preset", methods=['GET'])
@require_auth
@with_logto_token
def query_apportion_preset():
    uid = g.current_user["sub"]
    org = get_organizations_by_uid(uid)
    if org is None:
        return make_response('', 204)
    
    org_map = {o["id"]: o for o in org}
    org_members = {
        oid: get_organizations_member_by_id(oid)
        for oid in org_map
    }
    
    stmt = select(ApportionPreset).where(ApportionPreset.oid.in_(org_map))
    presets: List[ApportionPreset] = db.session.execute(stmt).scalars().all()
    if len(presets) == 0:
        return make_response('', 204)
    
    result = []
    for preset in presets:
        stmt = select(ApportionPresetDetail).where(
            ApportionPresetDetail.apportion_preset_id == preset.id,
            ApportionPresetDetail.uid.in_([u["id"] for u in org_members.get(preset.oid)])
        )
        details_result = db.session.execute(stmt)
        details: List[ApportionPresetDetail] = details_result.scalars().all()

        result.append({
            "name": preset.name,
            "org": org_map[preset.oid]["name"],
            "method": preset.method.value,
            "details": [{
                "uid": detail.uid,
                "username": get_user_by_id(detail.uid)["username"],
                "value": detail.value
            } for detail in details]
        })

    return jsonify(result)


@bill.route("/create", methods=['POST'])
@require_auth
@with_logto_token
def create_bill():
    try:
        data = ValidatedBill(**request.get_json())

        party = Party()
        db.session.add(party)
        db.session.flush()
        puser = PartyUser()
        puser.party_id = party.id
        puser.uid = data.party
        db.session.add(puser)

        counterparty = Party()
        db.session.add(counterparty)
        db.session.flush()
        for uid in data.counterparty:
            puser = PartyUser()
            puser.party_id = counterparty.id
            puser.uid = uid
            db.session.add(puser)

        new_bill = Bill()
        new_bill.trade_time = data.trade_time
        new_bill.title = data.title
        new_bill.description = data.description
        new_bill.price = data.price
        new_bill.party_id = party.id
        new_bill.counterparty_id = counterparty.id
        db.session.add(new_bill)
        db.session.flush()

        # apportion
        payer_uid = data.party
        counterparty_uids = data.counterparty
        apportions_map = {ap.user: ap.value for ap in data.apportions}
        total_price = data.price
        method = data.apportion_method


        apportion = Apportion()
        apportion.bill_id=new_bill.id
        apportion.method=method
        db.session.add(apportion)
        db.session.flush()

        for uid in counterparty_uids:
            apportion_detail = ApportionDetail()
            apportion_detail.apportion_id=apportion.id
            apportion_detail.uid=uid
            apportion_detail.value=apportions_map.get(uid)
            db.session.add(apportion_detail)
        
        # apportion preset
        if data.as_apportion_preset:
            preset = ApportionPreset()
            preset.name = data.apportion_preset_title
            preset.oid = data.apportion_preset_organization_id
            preset.method = method
            db.session.add(preset)
            db.session.flush()

            for uid in counterparty_uids:
                preset_detail = ApportionPresetDetail()
                preset_detail.apportion_preset_id = preset.id
                preset_detail.uid = uid
                preset_detail.value = apportions_map.get(uid)
                db.session.add(preset_detail)

        # bill amount
        amounts: Dict[str, BillAmount] = {}
        for uid in counterparty_uids:
            amounts[uid] = BillAmount()
            amounts[uid].bill_id=new_bill.id
            amounts[uid].uid=uid
            amounts[uid].price=Decimal('0')
            amounts[uid].diff=Decimal('0')
            amounts[uid].completed=False
        amounts[payer_uid] = BillAmount()
        amounts[payer_uid].bill_id=new_bill.id
        amounts[payer_uid].uid=payer_uid
        amounts[payer_uid].price=data.price
        amounts[payer_uid].diff=-data.price
        amounts[payer_uid].completed=False

        # calculate diff
        if method == ApportionMethod.price:
            owed = {uid: apportions_map.get(uid, Decimal('0')) for uid in counterparty_uids}
        elif method == ApportionMethod.ratio:
            owed = {
                uid: (total_price * apportions_map[uid] / Decimal('100')).quantize(Decimal('0.01'))
                for uid in counterparty_uids
            }
        elif method == ApportionMethod.share:
            total_share = sum(apportions_map[uid] for uid in counterparty_uids)
            owed = {
                uid: (total_price * apportions_map[uid] / total_share).quantize(Decimal('0.01'))
                for uid in counterparty_uids
            }
        else:
            abort(400)

        # handle round-off error
        diff = total_price - sum(owed.values(), Decimal('0'))
        if diff != Decimal('0'):
            owed[choice(counterparty_uids)] += diff

        # update diff
        for uid in counterparty_uids:
            amounts[uid].diff += owed[uid]

        # insert amount
        for uid in amounts:
            db.session.add(amounts[uid])

        db.session.commit()
        return make_response('', 201)

    except (ValueError, TypeError) as e:
        print(e)
        db.session.rollback()
        abort(400)
    except Exception as e:
        print(e)
        db.session.rollback()
        abort(500)
