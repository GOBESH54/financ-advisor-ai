import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class TaxPlanner:
    """Indian tax planning with 80C, HRA, capital gains"""
    
    def __init__(self):
        self.tax_slabs_old = [
            (250000, 0), (500000, 0.05), (1000000, 0.20), (float('inf'), 0.30)
        ]
        self.tax_slabs_new = [
            (300000, 0), (600000, 0.05), (900000, 0.10), (1200000, 0.15),
            (1500000, 0.20), (float('inf'), 0.30)
        ]
        
        self.section_80c_limit = 150000
        self.hra_exemption_rates = {'metro': 0.50, 'non_metro': 0.40}
    
    def calculate_tax(self, annual_income: float, investments_80c: float = 0, 
                     hra_received: float = 0, rent_paid: float = 0, 
                     is_metro: bool = True, regime: str = 'old') -> Dict:
        """Calculate income tax with deductions"""
        
        # Choose tax regime
        slabs = self.tax_slabs_old if regime == 'old' else self.tax_slabs_new
        
        # Standard deduction
        standard_deduction = 50000 if regime == 'old' else 50000
        
        # 80C deductions (only for old regime)
        deduction_80c = min(investments_80c, self.section_80c_limit) if regime == 'old' else 0
        
        # HRA exemption (only for old regime)
        hra_exemption = 0
        if regime == 'old' and hra_received > 0 and rent_paid > 0:
            basic_salary = annual_income * 0.5  # Assume 50% is basic
            rate = self.hra_exemption_rates['metro' if is_metro else 'non_metro']
            
            hra_exemption = min(
                hra_received,
                rent_paid - (basic_salary * 0.10),
                basic_salary * rate
            )
            hra_exemption = max(0, hra_exemption)
        
        # Taxable income
        taxable_income = annual_income - standard_deduction - deduction_80c - hra_exemption
        taxable_income = max(0, taxable_income)
        
        # Calculate tax
        tax = 0
        remaining_income = taxable_income
        
        for i, (limit, rate) in enumerate(slabs):
            if remaining_income <= 0:
                break
            
            prev_limit = slabs[i-1][0] if i > 0 else 0
            taxable_in_slab = min(remaining_income, limit - prev_limit)
            
            tax += taxable_in_slab * rate
            remaining_income -= taxable_in_slab
        
        # Health and education cess (4%)
        cess = tax * 0.04
        total_tax = tax + cess
        
        return {
            'annual_income': annual_income,
            'taxable_income': taxable_income,
            'tax_before_cess': tax,
            'cess': cess,
            'total_tax': total_tax,
            'effective_tax_rate': (total_tax / annual_income) * 100,
            'deductions': {
                'standard_deduction': standard_deduction,
                '80c_deduction': deduction_80c,
                'hra_exemption': hra_exemption,
                'total_deductions': standard_deduction + deduction_80c + hra_exemption
            },
            'tax_regime': regime,
            'savings_vs_other_regime': self._compare_regimes(annual_income, investments_80c, hra_received, rent_paid, is_metro, regime)
        }
    
    def _compare_regimes(self, income: float, inv_80c: float, hra: float, rent: float, metro: bool, current: str) -> float:
        """Compare tax between old and new regime"""
        other_regime = 'new' if current == 'old' else 'old'
        
        current_tax = self.calculate_tax(income, inv_80c, hra, rent, metro, current)['total_tax']
        other_tax = self.calculate_tax(income, inv_80c, hra, rent, metro, other_regime)['total_tax']
        
        return other_tax - current_tax  # Positive means current regime saves money
    
    def calculate_capital_gains(self, purchase_price: float, sale_price: float, 
                              purchase_date: datetime, sale_date: datetime, 
                              asset_type: str = 'equity') -> Dict:
        """Calculate capital gains tax"""
        
        holding_period = (sale_date - purchase_date).days
        gain = sale_price - purchase_price
        
        if gain <= 0:
            return {'gain': gain, 'tax': 0, 'type': 'loss'}
        
        if asset_type == 'equity':
            if holding_period > 365:  # Long term
                # LTCG > 1 lakh taxed at 10%
                exemption = 100000
                taxable_gain = max(0, gain - exemption)
                tax = taxable_gain * 0.10
                gain_type = 'long_term'
            else:  # Short term
                tax = gain * 0.15  # STCG at 15%
                gain_type = 'short_term'
        else:  # Other assets
            if holding_period > 1095:  # 3 years for other assets
                # LTCG at 20% with indexation
                indexed_cost = purchase_price * 1.05  # Simplified indexation
                indexed_gain = sale_price - indexed_cost
                tax = max(0, indexed_gain) * 0.20
                gain_type = 'long_term'
            else:
                tax = gain * 0.30  # As per income tax slab
                gain_type = 'short_term'
        
        return {
            'gain': gain,
            'tax': tax,
            'type': gain_type,
            'holding_period_days': holding_period,
            'effective_rate': (tax / gain) * 100 if gain > 0 else 0
        }

class GSTTracker:
    """GST tracking for business expenses"""
    
    def __init__(self):
        self.gst_rates = {
            'essential': 0.05,
            'standard': 0.12,
            'luxury': 0.18,
            'premium': 0.28
        }
    
    def calculate_gst(self, amount: float, gst_rate: float = 0.18, inclusive: bool = True) -> Dict:
        """Calculate GST breakdown"""
        
        if inclusive:
            # Amount includes GST
            base_amount = amount / (1 + gst_rate)
            gst_amount = amount - base_amount
        else:
            # Amount excludes GST
            base_amount = amount
            gst_amount = amount * gst_rate
            amount = base_amount + gst_amount
        
        cgst = sgst = gst_amount / 2  # For intra-state
        igst = gst_amount  # For inter-state
        
        return {
            'total_amount': amount,
            'base_amount': base_amount,
            'gst_amount': gst_amount,
            'gst_rate': gst_rate * 100,
            'cgst': cgst,
            'sgst': sgst,
            'igst': igst,
            'is_inclusive': inclusive
        }
    
    def track_gst_expenses(self, expenses_df: pd.DataFrame) -> Dict:
        """Track GST from business expenses"""
        
        if expenses_df.empty:
            return {'total_gst': 0, 'breakdown': {}}
        
        total_gst = 0
        category_gst = {}
        
        for _, expense in expenses_df.iterrows():
            # Assume 18% GST for business expenses
            gst_calc = self.calculate_gst(expense['amount'], 0.18, True)
            gst_amount = gst_calc['gst_amount']
            
            total_gst += gst_amount
            category = expense.get('category', 'other')
            
            if category not in category_gst:
                category_gst[category] = 0
            category_gst[category] += gst_amount
        
        return {
            'total_gst_paid': total_gst,
            'category_breakdown': category_gst,
            'itc_eligible': total_gst * 0.8,  # Assume 80% ITC eligible
            'net_gst_liability': total_gst * 0.2
        }

class InvestmentTracker:
    """Track mutual funds, stocks, FDs, PPF"""
    
    def __init__(self):
        self.fd_rates = {'sbi': 0.065, 'hdfc': 0.067, 'icici': 0.066}
        self.ppf_rate = 0.071  # Current PPF rate
    
    def calculate_sip_returns(self, monthly_amount: float, annual_return: float, 
                            years: int) -> Dict:
        """Calculate SIP returns"""
        
        months = years * 12
        monthly_rate = annual_return / 12
        
        # Future value of SIP
        if monthly_rate > 0:
            future_value = monthly_amount * (((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate)
        else:
            future_value = monthly_amount * months
        
        total_invested = monthly_amount * months
        returns = future_value - total_invested
        
        return {
            'monthly_sip': monthly_amount,
            'total_invested': total_invested,
            'future_value': future_value,
            'returns': returns,
            'return_percentage': (returns / total_invested) * 100,
            'years': years,
            'annual_return_assumed': annual_return * 100
        }
    
    def calculate_fd_returns(self, principal: float, rate: float, years: float, 
                           compound_frequency: int = 4) -> Dict:
        """Calculate FD returns with quarterly compounding"""
        
        # Compound interest formula
        amount = principal * (1 + rate / compound_frequency) ** (compound_frequency * years)
        interest = amount - principal
        
        return {
            'principal': principal,
            'maturity_amount': amount,
            'interest_earned': interest,
            'rate': rate * 100,
            'years': years,
            'effective_yield': (interest / principal) * 100
        }
    
    def calculate_ppf_returns(self, annual_contribution: float, years: int = 15) -> Dict:
        """Calculate PPF returns (15-year lock-in)"""
        
        if years < 15:
            years = 15  # Minimum PPF tenure
        
        rate = self.ppf_rate
        total_contribution = 0
        balance = 0
        
        for year in range(years):
            contribution = min(annual_contribution, 150000)  # PPF limit
            total_contribution += contribution
            balance = (balance + contribution) * (1 + rate)
        
        returns = balance - total_contribution
        
        return {
            'annual_contribution': annual_contribution,
            'total_contribution': total_contribution,
            'maturity_amount': balance,
            'returns': returns,
            'return_percentage': (returns / total_contribution) * 100,
            'years': years,
            'tax_free_returns': True,
            '80c_benefit': min(total_contribution, 150000 * years)
        }
    
    def portfolio_analysis(self, investments: List[Dict]) -> Dict:
        """Analyze investment portfolio"""
        
        total_value = sum(inv['current_value'] for inv in investments)
        total_invested = sum(inv['invested_amount'] for inv in investments)
        
        if total_invested == 0:
            return {'error': 'No investments found'}
        
        # Asset allocation
        allocation = {}
        for inv in investments:
            asset_type = inv['type']
            if asset_type not in allocation:
                allocation[asset_type] = 0
            allocation[asset_type] += inv['current_value']
        
        # Convert to percentages
        allocation_pct = {k: (v / total_value) * 100 for k, v in allocation.items()}
        
        # Overall returns
        total_returns = total_value - total_invested
        return_pct = (total_returns / total_invested) * 100
        
        return {
            'total_invested': total_invested,
            'current_value': total_value,
            'total_returns': total_returns,
            'return_percentage': return_pct,
            'asset_allocation': allocation_pct,
            'diversification_score': len(allocation),  # Simple diversification metric
            'top_performer': max(investments, key=lambda x: (x['current_value'] - x['invested_amount']) / x['invested_amount'])['name']
        }

class EMICalculator:
    """Loan planning and EMI optimization"""
    
    def calculate_emi(self, principal: float, rate: float, tenure_months: int) -> Dict:
        """Calculate EMI using standard formula"""
        
        monthly_rate = rate / (12 * 100)
        
        if monthly_rate == 0:
            emi = principal / tenure_months
        else:
            emi = principal * monthly_rate * (1 + monthly_rate) ** tenure_months / ((1 + monthly_rate) ** tenure_months - 1)
        
        total_payment = emi * tenure_months
        total_interest = total_payment - principal
        
        return {
            'principal': principal,
            'emi': emi,
            'tenure_months': tenure_months,
            'tenure_years': tenure_months / 12,
            'total_payment': total_payment,
            'total_interest': total_interest,
            'interest_rate': rate,
            'interest_percentage': (total_interest / principal) * 100
        }
    
    def loan_comparison(self, principal: float, options: List[Dict]) -> List[Dict]:
        """Compare multiple loan options"""
        
        comparisons = []
        
        for option in options:
            emi_calc = self.calculate_emi(
                principal, 
                option['rate'], 
                option['tenure_months']
            )
            
            emi_calc.update({
                'bank': option.get('bank', 'Unknown'),
                'loan_type': option.get('type', 'Personal')
            })
            
            comparisons.append(emi_calc)
        
        # Sort by total interest (lowest first)
        comparisons.sort(key=lambda x: x['total_interest'])
        
        return comparisons
    
    def prepayment_analysis(self, principal: float, rate: float, tenure_months: int, 
                          prepayment_amount: float, prepayment_month: int) -> Dict:
        """Analyze impact of prepayment"""
        
        # Original loan
        original = self.calculate_emi(principal, rate, tenure_months)
        
        # Calculate remaining principal at prepayment month
        monthly_rate = rate / (12 * 100)
        emi = original['emi']
        
        remaining_principal = principal
        for month in range(prepayment_month):
            interest_component = remaining_principal * monthly_rate
            principal_component = emi - interest_component
            remaining_principal -= principal_component
        
        # New loan after prepayment
        new_principal = remaining_principal - prepayment_amount
        new_tenure = tenure_months - prepayment_month
        
        if new_principal <= 0:
            return {
                'loan_closed': True,
                'savings': original['total_payment'] - (emi * prepayment_month + prepayment_amount)
            }
        
        new_loan = self.calculate_emi(new_principal, rate, new_tenure)
        
        # Calculate savings
        original_remaining_payment = emi * new_tenure
        new_total_payment = new_loan['total_payment']
        interest_savings = original_remaining_payment - new_total_payment
        
        return {
            'original_loan': original,
            'prepayment_amount': prepayment_amount,
            'prepayment_month': prepayment_month,
            'new_emi': new_loan['emi'],
            'new_tenure_months': new_tenure,
            'interest_savings': interest_savings,
            'total_savings': interest_savings,
            'payback_months': prepayment_amount / interest_savings if interest_savings > 0 else float('inf')
        }
    
    def optimal_loan_tenure(self, principal: float, rate: float, max_emi: float) -> Dict:
        """Find optimal tenure based on EMI affordability"""
        
        monthly_rate = rate / (12 * 100)
        
        if monthly_rate == 0:
            optimal_tenure = int(principal / max_emi)
        else:
            # Solve for tenure using EMI formula
            optimal_tenure = int(-np.log(1 - (principal * monthly_rate) / max_emi) / np.log(1 + monthly_rate))
        
        optimal_tenure = max(12, optimal_tenure)  # Minimum 1 year
        
        loan_details = self.calculate_emi(principal, rate, optimal_tenure)
        
        return {
            'optimal_tenure_months': optimal_tenure,
            'optimal_tenure_years': optimal_tenure / 12,
            'emi': loan_details['emi'],
            'total_interest': loan_details['total_interest'],
            'max_affordable_emi': max_emi,
            'emi_utilization': (loan_details['emi'] / max_emi) * 100
        }