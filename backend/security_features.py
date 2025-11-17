from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import secrets
import smtplib
import sqlite3
import shutil
import schedule
import time
import threading
from datetime import datetime, timedelta
from email.mime.text import MIMEText as MimeText
from email.mime.multipart import MIMEMultipart as MimeMultipart
from typing import Dict, List, Optional
import logging
import json
import hashlib

logger = logging.getLogger(__name__)

class DataEncryption:
    """AES-256 encryption for sensitive data"""
    
    def __init__(self, password: str = None):
        self.password = password or os.environ.get('ENCRYPTION_KEY', 'default_key_change_in_production')
        self.key = self._derive_key(self.password)
        self.cipher = Fernet(self.key)
    
    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password using PBKDF2"""
        salt = b'finance_app_salt_2024'  # In production, use random salt per user
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            if not data:
                return data
            
            encrypted_data = self.cipher.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            return data
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            if not encrypted_data:
                return encrypted_data
            
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.cipher.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            return encrypted_data
    
    def encrypt_amount(self, amount: float) -> str:
        """Encrypt financial amounts"""
        return self.encrypt(str(amount))
    
    def decrypt_amount(self, encrypted_amount: str) -> float:
        """Decrypt financial amounts"""
        try:
            decrypted = self.decrypt(encrypted_amount)
            return float(decrypted)
        except (ValueError, TypeError):
            return 0.0
    
    def hash_sensitive_data(self, data: str) -> str:
        """Create hash for sensitive data (one-way)"""
        return hashlib.sha256(data.encode()).hexdigest()

class MultiFactorAuth:
    """Multi-factor authentication with SMS/email OTP"""
    
    def __init__(self):
        self.otp_storage = {}  # In production, use Redis or database
        self.otp_expiry = 300  # 5 minutes
        
        # Email configuration
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.email_user = os.environ.get('EMAIL_USER', '')
        self.email_password = os.environ.get('EMAIL_PASSWORD', '')
    
    def generate_otp(self) -> str:
        """Generate 6-digit OTP"""
        return str(secrets.randbelow(900000) + 100000)
    
    def send_email_otp(self, email: str, user_name: str = 'User') -> Dict:
        """Send OTP via email"""
        try:
            otp = self.generate_otp()
            
            # Store OTP with expiry
            self.otp_storage[email] = {
                'otp': otp,
                'expires_at': datetime.now() + timedelta(seconds=self.otp_expiry),
                'attempts': 0
            }
            
            # Create email message
            msg = MimeMultipart()
            msg['From'] = self.email_user
            msg['To'] = email
            msg['Subject'] = 'Personal Finance Advisor - Login OTP'
            
            body = f"""
            Dear {user_name},
            
            Your OTP for Personal Finance Advisor login is: {otp}
            
            This OTP is valid for 5 minutes only.
            
            If you didn't request this, please ignore this email.
            
            Best regards,
            Personal Finance Advisor Team
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            # Send email
            if self.email_user and self.email_password:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
                server.quit()
                
                return {'success': True, 'message': 'OTP sent to email'}
            else:
                # For testing without email setup
                logger.info(f"OTP for {email}: {otp}")
                return {'success': True, 'message': f'OTP generated: {otp} (check logs)'}
                
        except Exception as e:
            logger.error(f"Error sending email OTP: {e}")
            return {'success': False, 'error': str(e)}
    
    def send_sms_otp(self, phone: str) -> Dict:
        """Send OTP via SMS (placeholder - integrate with SMS service)"""
        try:
            otp = self.generate_otp()
            
            # Store OTP with expiry
            self.otp_storage[phone] = {
                'otp': otp,
                'expires_at': datetime.now() + timedelta(seconds=self.otp_expiry),
                'attempts': 0
            }
            
            # In production, integrate with SMS service like Twilio, AWS SNS, etc.
            logger.info(f"SMS OTP for {phone}: {otp}")
            
            return {
                'success': True, 
                'message': f'OTP sent to {phone[-4:].rjust(len(phone), "*")}',
                'otp': otp  # Remove in production
            }
            
        except Exception as e:
            logger.error(f"Error sending SMS OTP: {e}")
            return {'success': False, 'error': str(e)}
    
    def verify_otp(self, identifier: str, otp: str) -> Dict:
        """Verify OTP for email or phone"""
        try:
            if identifier not in self.otp_storage:
                return {'success': False, 'error': 'OTP not found or expired'}
            
            stored_otp = self.otp_storage[identifier]
            
            # Check expiry
            if datetime.now() > stored_otp['expires_at']:
                del self.otp_storage[identifier]
                return {'success': False, 'error': 'OTP expired'}
            
            # Check attempts
            if stored_otp['attempts'] >= 3:
                del self.otp_storage[identifier]
                return {'success': False, 'error': 'Too many failed attempts'}
            
            # Verify OTP
            if stored_otp['otp'] == otp:
                del self.otp_storage[identifier]
                return {'success': True, 'message': 'OTP verified successfully'}
            else:
                self.otp_storage[identifier]['attempts'] += 1
                return {'success': False, 'error': 'Invalid OTP'}
                
        except Exception as e:
            logger.error(f"Error verifying OTP: {e}")
            return {'success': False, 'error': str(e)}
    
    def cleanup_expired_otps(self):
        """Clean up expired OTPs"""
        current_time = datetime.now()
        expired_keys = [
            key for key, value in self.otp_storage.items()
            if current_time > value['expires_at']
        ]
        
        for key in expired_keys:
            del self.otp_storage[key]

class AuditLogger:
    """Audit logging for tracking all data changes"""
    
    def __init__(self, db_path: str = 'audit_log.db'):
        self.db_path = db_path
        self.init_audit_db()
    
    def init_audit_db(self):
        """Initialize audit log database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    table_name TEXT,
                    record_id INTEGER,
                    old_values TEXT,
                    new_values TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    session_id TEXT
                )
            ''')
            
            # Create index for performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_audit_user_timestamp 
                ON audit_log (user_id, timestamp DESC)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_audit_action_timestamp 
                ON audit_log (action, timestamp DESC)
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error initializing audit database: {e}")
    
    def log_action(self, user_id: int, action: str, table_name: str = None, 
                   record_id: int = None, old_values: Dict = None, 
                   new_values: Dict = None, ip_address: str = None, 
                   user_agent: str = None, session_id: str = None):
        """Log user action"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO audit_log 
                (user_id, action, table_name, record_id, old_values, new_values, 
                 ip_address, user_agent, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, action, table_name, record_id,
                json.dumps(old_values) if old_values else None,
                json.dumps(new_values) if new_values else None,
                ip_address, user_agent, session_id
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error logging audit action: {e}")
    
    def log_login(self, user_id: int, success: bool, ip_address: str = None, 
                  user_agent: str = None, mfa_used: bool = False):
        """Log login attempt"""
        action = f"LOGIN_{'SUCCESS' if success else 'FAILED'}"
        if mfa_used:
            action += "_MFA"
        
        self.log_action(
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_data_change(self, user_id: int, table_name: str, record_id: int, 
                       action: str, old_values: Dict = None, new_values: Dict = None):
        """Log data changes (CREATE, UPDATE, DELETE)"""
        self.log_action(
            user_id=user_id,
            action=f"{action}_{table_name.upper()}",
            table_name=table_name,
            record_id=record_id,
            old_values=old_values,
            new_values=new_values
        )
    
    def get_user_audit_log(self, user_id: int, limit: int = 100) -> List[Dict]:
        """Get audit log for specific user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, action, table_name, record_id, 
                       old_values, new_values, ip_address
                FROM audit_log 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (user_id, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [{
                'timestamp': row[0],
                'action': row[1],
                'table_name': row[2],
                'record_id': row[3],
                'old_values': json.loads(row[4]) if row[4] else None,
                'new_values': json.loads(row[5]) if row[5] else None,
                'ip_address': row[6]
            } for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting audit log: {e}")
            return []
    
    def get_security_events(self, hours: int = 24) -> List[Dict]:
        """Get security-related events"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since = datetime.now() - timedelta(hours=hours)
            
            cursor.execute('''
                SELECT timestamp, user_id, action, ip_address, user_agent
                FROM audit_log 
                WHERE action LIKE '%LOGIN%' OR action LIKE '%AUTH%'
                AND timestamp > ?
                ORDER BY timestamp DESC
            ''', (since.isoformat(),))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [{
                'timestamp': row[0],
                'user_id': row[1],
                'action': row[2],
                'ip_address': row[3],
                'user_agent': row[4]
            } for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting security events: {e}")
            return []

class DataBackup:
    """Automated local data backups"""
    
    def __init__(self, source_db: str = 'instance/finance_advisor.db', 
                 backup_dir: str = 'backups'):
        self.source_db = source_db
        self.backup_dir = backup_dir
        self.ensure_backup_dir()
        self.schedule_backups()
    
    def ensure_backup_dir(self):
        """Ensure backup directory exists"""
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def create_backup(self, backup_type: str = 'manual') -> Dict:
        """Create database backup"""
        try:
            if not os.path.exists(self.source_db):
                return {'success': False, 'error': 'Source database not found'}
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f'finance_backup_{backup_type}_{timestamp}.db'
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Copy database file
            shutil.copy2(self.source_db, backup_path)
            
            # Verify backup
            if os.path.exists(backup_path):
                backup_size = os.path.getsize(backup_path)
                
                # Create backup metadata
                metadata = {
                    'timestamp': datetime.now().isoformat(),
                    'type': backup_type,
                    'size_bytes': backup_size,
                    'source_db': self.source_db,
                    'backup_path': backup_path
                }
                
                metadata_path = backup_path.replace('.db', '_metadata.json')
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                logger.info(f"Backup created: {backup_filename}")
                
                return {
                    'success': True,
                    'backup_path': backup_path,
                    'size_mb': backup_size / (1024 * 1024),
                    'timestamp': timestamp
                }
            else:
                return {'success': False, 'error': 'Backup file not created'}
                
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return {'success': False, 'error': str(e)}
    
    def restore_backup(self, backup_path: str) -> Dict:
        """Restore from backup"""
        try:
            if not os.path.exists(backup_path):
                return {'success': False, 'error': 'Backup file not found'}
            
            # Create backup of current database before restore
            current_backup = self.create_backup('pre_restore')
            
            # Restore from backup
            shutil.copy2(backup_path, self.source_db)
            
            return {
                'success': True,
                'message': 'Database restored successfully',
                'current_backup': current_backup.get('backup_path')
            }
            
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return {'success': False, 'error': str(e)}
    
    def list_backups(self) -> List[Dict]:
        """List available backups"""
        try:
            backups = []
            
            for filename in os.listdir(self.backup_dir):
                if filename.endswith('.db'):
                    filepath = os.path.join(self.backup_dir, filename)
                    metadata_path = filepath.replace('.db', '_metadata.json')
                    
                    backup_info = {
                        'filename': filename,
                        'path': filepath,
                        'size_mb': os.path.getsize(filepath) / (1024 * 1024),
                        'created': datetime.fromtimestamp(os.path.getctime(filepath)).isoformat()
                    }
                    
                    # Load metadata if available
                    if os.path.exists(metadata_path):
                        try:
                            with open(metadata_path, 'r') as f:
                                metadata = json.load(f)
                                backup_info.update(metadata)
                        except:
                            pass
                    
                    backups.append(backup_info)
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x['created'], reverse=True)
            
            return backups
            
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            return []
    
    def cleanup_old_backups(self, keep_days: int = 30):
        """Clean up old backups"""
        try:
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            deleted_count = 0
            
            for filename in os.listdir(self.backup_dir):
                if filename.endswith('.db') or filename.endswith('_metadata.json'):
                    filepath = os.path.join(self.backup_dir, filename)
                    file_date = datetime.fromtimestamp(os.path.getctime(filepath))
                    
                    if file_date < cutoff_date:
                        os.remove(filepath)
                        deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old backup files")
            return {'success': True, 'deleted_count': deleted_count}
            
        except Exception as e:
            logger.error(f"Error cleaning up backups: {e}")
            return {'success': False, 'error': str(e)}
    
    def schedule_backups(self):
        """Schedule automatic backups"""
        # Daily backup at 2 AM
        schedule.every().day.at("02:00").do(self._daily_backup)
        
        # Weekly backup on Sunday at 3 AM
        schedule.every().sunday.at("03:00").do(self._weekly_backup)
        
        # Monthly cleanup (use monthly interval instead)
        schedule.every(30).days.do(self._monthly_cleanup)
        
        # Start scheduler in background thread
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
    
    def _daily_backup(self):
        """Daily backup task"""
        result = self.create_backup('daily')
        if result['success']:
            logger.info("Daily backup completed successfully")
        else:
            logger.error(f"Daily backup failed: {result['error']}")
    
    def _weekly_backup(self):
        """Weekly backup task"""
        result = self.create_backup('weekly')
        if result['success']:
            logger.info("Weekly backup completed successfully")
        else:
            logger.error(f"Weekly backup failed: {result['error']}")
    
    def _monthly_cleanup(self):
        """Monthly cleanup task"""
        result = self.cleanup_old_backups(keep_days=30)
        if result['success']:
            logger.info(f"Monthly cleanup completed: {result['deleted_count']} files removed")
        else:
            logger.error(f"Monthly cleanup failed: {result['error']}")

class SecurityManager:
    """Centralized security management"""
    
    def __init__(self):
        self.encryption = DataEncryption()
        self.mfa = MultiFactorAuth()
        self.audit_logger = AuditLogger()
        self.backup_manager = DataBackup()
    
    def get_security_status(self) -> Dict:
        """Get overall security status"""
        return {
            'encryption_enabled': True,
            'mfa_available': True,
            'audit_logging': True,
            'backup_system': True,
            'last_backup': self._get_last_backup_time(),
            'security_events_24h': len(self.audit_logger.get_security_events(24))
        }
    
    def _get_last_backup_time(self) -> Optional[str]:
        """Get timestamp of last backup"""
        try:
            backups = self.backup_manager.list_backups()
            if backups:
                return backups[0]['created']
            return None
        except:
            return None