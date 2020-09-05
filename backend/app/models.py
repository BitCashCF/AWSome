from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from passlib.apps import custom_app_context as pwd_context

from itsdangerous import (TimedJSONWebSignatureSerializer
                            as Serializer, BadSignature, SignatureExpired)

from Config import SECRET_KEY
from db import session

from Bloomberg import get_bb_id, get_bb_statistics, get_bb_financials
from YahooAPI import get_yf_id, get_yf_analysis, get_yf_financials

Base = declarative_base()
    

class SportSpot(Base):

    __tablename__ = 'spots'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(80))
    address = Column(String(200))
    author_id = Column(Integer, ForeignKey('users.id'))

    def __repr__(self):
        return '<Spot %r>' % self.title


class User(Base):
    
    __tablename__ = 'users'

    id = Column(Integer, primary_key = True)
    username = Column(String(32), index = True)
    password_hash = Column(String(128))
    risk_level = Column(Integer, default=-1)
    retirement_amount = Column(Integer, default=-1)
    years_till_retire = Column(Integer, default=-1)
    expected_growth = Column(Float, default=-1)
    monthly_deposit = Column(Float, default=-1)

    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

    def generate_auth_token(self, expiration = 60000):
        s = Serializer(SECRET_KEY, expires_in = expiration)
        return s.dumps({ 'id': self.id })

    def update_questionnaire(self, data):
        self.risk_level = data['risk_level']
        self.retirement_amount = data['retirement_amount']
        self.years_till_retire = data['years_till_retire']

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(SECRET_KEY)
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None # valid token, but expired
        except BadSignature:
            return None # invalid token
        user = session.query(User).filter(User.id == data['id']).first()
        return user

class SPFH(Base):
    
    __tablename__ = 'spfh'

    id = Column(Integer, primary_key = True)
    name = Column(String(64), index = True)
    bb_id = Column(String(16))
    yf_id = Column(String(16))

    market_cap = Column(Float)
    total_asset = Column(Float)
    debt = Column(Float)
    gross_profit = Column(Float)
    beta = Column(Float)

    revenue_3y_bk = Column(Float)
    revenue_1y_bk = Column(Float)
    revenue_1y_fd = Column(Float)

    current_pe = Column(Float)
    est_peg = Column(Float)
    dividend = Column(Float)
    ave_vol = Column(Float)

    gpta = Column(Float)
    ave_sales_growth = Column(Float)
    debt_to_mcap = Column(Float)

    def set_id(self, name):
        self.bb_id = get_bb_id(name)
        self.yf_id = get_yf_id(name)

    def set_bb_metrics(self):
        statistics_dict = get_bb_statistics(self.bb_id)
        financials_dict = get_bb_financials(self.bb_id)
        statistics_dict.update(financials_dict)
        bb_dict = statistics_dict.copy()

        self.current_pe = bb_dict["Current P/E Ratio (ttm)"]
        self.est_peg = bb_dict["Est. PEG Ratio"]
        self.dividend = bb_dict["Dividend Indicated Gross Yield"]
        self.ave_vol = bb_dict["Average Volume (30-day)"]

        self.market_cap = bb_dict["Market Cap (M)"] * 1000000
        self.total_asset = bb_dict["Total Assets"]
        self.debt = round(bb_dict["Total Assets"] * bb_dict["Debt to Assets"] / 100, 2)
        
        self.revenue_3y_bk = bb_dict["Revenue -3y"]
        self.revenue_1y_bk = bb_dict["Revenue -1y"]


    def set_yf_metrics(self):
        analysis_dict = get_yf_analysis(self.yf_id)
        financial_dict = get_yf_financials(self.yf_id)
        analysis_dict.update(financial_dict)
        yf_dict= analysis_dict.copy()

        self.gross_profit = yf_dict['Gross Profit']
        self.revenue_1y_fd = yf_dict['Revenue +1y']
        self.beta = yf_dict['Beta']
    
    def calc_derived_metrics(self):
        self.debt_to_mcap = round(self.debt / self.market_cap, 6)
        self.gpta = round(self.gross_profit / self.total_asset, 6)

        prev_growth_r = ( (self.revenue_1y_bk / self.revenue_3y_bk) ** 0.5 ) - 1
        future_growth_r = ( (self.revenue_1y_fd / self.revenue_1y_bk) ** 0.5 ) - 1
        self.ave_sales_growth = round( (prev_growth_r + future_growth_r) / 2, 6)


if __name__ == "__main__":
    from sqlalchemy import create_engine
    from Config import DB_URI
    engine = create_engine(DB_URI)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)




