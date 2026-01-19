from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator
from typing import List, Any
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime


from common.util import get_user_by_id
from bill.db import ApportionMethod


class ApportionItem(BaseModel):
    user: str = Field(..., min_length=1, max_length=32)
    value: Decimal = Field(..., ge=0)

    @field_validator('value', mode='before')
    @classmethod
    def validate_value(cls, v: Any) -> Decimal:
        try:
            return Decimal(str(v)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except Exception:
            raise ValueError('value must be a valid number with at most 2 decimal places')


class ValidatedBill(BaseModel):
    title: str = Field(..., min_length=1)
    trade_time: datetime
    description: str = ""
    price: Decimal = Field(..., gt=0)
    party: str = Field(..., min_length=1, max_length=32)
    counterparty: List[str] = Field(..., min_items=1)
    apportion_method: ApportionMethod
    apportions: List[ApportionItem] = Field(..., min_items=1)
    as_apportion_preset: bool
    apportion_preset_title: str = ""
    apportion_preset_organization_id: str = ""

    @field_validator('price', mode='before')
    @classmethod
    def validate_price(cls, v: Any) -> Decimal:
        try:
            return Decimal(str(v)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except Exception:
            raise ValueError('price must be a valid number with at most 2 decimal places')

    @field_validator('trade_time', mode='before')
    @classmethod
    def validate_trade_time(cls, v: str) -> datetime:
        try:
            dt = datetime.fromisoformat(v)
            if dt.tzinfo is None:
                raise ValueError('trade_time must include timezone info')
            return dt
        except (ValueError, TypeError) as e:
            raise ValueError(f'Invalid ISO 8601 datetime with timezone: {e}')

    @field_validator('counterparty')
    @classmethod
    def validate_counterparty(cls, v: List[str]) -> List[str]:
        for uid in v:
            if not isinstance(uid, str) or not (1 <= len(uid) <= 32):
                raise ValueError(f'Invalid UID format: {uid}')
        if len(v) != len(set(v)):
            raise ValueError('counterparty contains duplicate UIDs')
        return v

    @model_validator(mode='after')
    def check_apportions_and_uids(self, info: ValidationInfo) -> 'ValidatedBill':
        all_uids = {self.party} | set(self.counterparty)
        missing = [uid for uid in all_uids if get_user_by_id(uid) is None]
        if not all([get_user_by_id(uid) is not None for uid in all_uids]):
            raise ValueError(f"UID not found in account system: {missing}")

        apportion_users = [ap.user for ap in self.apportions]
        if len(apportion_users) != len(set(apportion_users)):
            raise ValueError('apportions contain duplicate users')
        counterparty_set = set(self.counterparty)
        if not set(apportion_users).issubset(counterparty_set):
            raise ValueError('All apportion users must be in counterparty list')

        # apportion rules
        method = self.apportion_method
        values = [ap.value for ap in self.apportions]
        total = sum(values, Decimal('0'))

        if method == ApportionMethod.price:
            if total != self.price:
                raise ValueError('Sum of apportion price must equal total price')

        elif method == ApportionMethod.ratio:
            if total != Decimal('100.00'):
                raise ValueError('Sum of apportion ratio must be exactly 100.00')

        elif method == ApportionMethod.share:
            if total == Decimal('0.00'):
                raise ValueError('Sum of apportion ratio must be bigger than 0')

        return self
