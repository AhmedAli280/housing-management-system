#!/usr/bin/env python3
"""
سكريبت إعداد النظام الجديد مع نظام KxYYZ
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from models.user import db
from models.core import setup_initial_data, Building, Room, Bed, Student
from datetime import datetime, date

def create_app():
    """إنشاء تطبيق Flask للإعداد"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///housing_system.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your-secret-key-here'
    
    db.init_app(app)
    return app

def setup_database():
    """إعداد قاعدة البيانات الجديدة"""
    app = create_app()
    
    with app.app_context():
        print("🔄 إنشاء الجداول...")
        db.create_all()
        
        print("🏢 إعداد المباني والغرف والأسرة...")
        setup_initial_data()
        
        print("📊 عرض الإحصائيات...")
        display_statistics()
        
        print("✅ تم إعداد النظام بنجاح!")

def display_statistics():
    """عرض إحصائيات النظام"""
    buildings = Building.query.all()
    total_beds = Bed.query.count()
    total_rooms = Room.query.count()
    
    print(f"\n📈 إحصائيات النظام:")
    print(f"عدد المباني: {len(buildings)}")
    print(f"إجمالي الغرف: {total_rooms}")
    print(f"إجمالي الأسرة: {total_beds}")
    print(f"الإيرادات المتوقعة: {total_beds * 55} ريال شهرياً")
    
    print(f"\n🏢 تفاصيل المباني:")
    for building in buildings:
        building_beds = Bed.query.filter_by(building_id=building.id).count()
        building_rooms = Room.query.filter_by(building_id=building.id).count()
        print(f"  {building.building_name} ({building.building_code}):")
        print(f"    - الغرف: {building_rooms}")
        print(f"    - الأسرة: {building_beds}")
        print(f"    - الإيرادات المتوقعة: {building_beds * 55} ريال")
    
    print(f"\n🛏️ أمثلة على أرقام الأسرة:")
    sample_beds = Bed.query.limit(10).all()
    for bed in sample_beds:
        room = Room.query.get(bed.room_id)
        building = Building.query.get(bed.building_id)
        print(f"  {bed.bed_code} - {building.building_name} غرفة {room.room_number} سرير {bed.bed_number}")

def add_sample_students():
    """إضافة طالبات تجريبية"""
    app = create_app()
    
    with app.app_context():
        sample_students = [
            {
                'name': 'فاطمة أحمد محمد',
                'phone': '0501234567',
                'national_id': '1234567890',
                'guardian_phone': '0509876543',
                'university': 'جامعة الملك سعود',
                'category': 'student',
                'rent_amount': 55.0,
                'security_deposit': 100.0,
                'contract_start': date(2025, 8, 1)
            },
            {
                'name': 'عائشة سالم علي',
                'phone': '0502345678',
                'national_id': '2345678901',
                'guardian_phone': '0508765432',
                'university': 'جامعة الأميرة نورة',
                'category': 'student',
                'rent_amount': 55.0,
                'security_deposit': 100.0,
                'contract_start': date(2025, 8, 1)
            },
            {
                'name': 'مريم خالد حسن',
                'phone': '0503456789',
                'national_id': '3456789012',
                'guardian_phone': '0507654321',
                'university': 'جامعة الإمام',
                'category': 'employee',
                'rent_amount': 55.0,
                'security_deposit': 100.0,
                'contract_start': date(2025, 8, 1)
            }
        ]
        
        print("👥 إضافة طالبات تجريبية...")
        
        for student_data in sample_students:
            existing = Student.query.filter_by(name=student_data['name']).first()
            if not existing:
                student = Student(**student_data)
                db.session.add(student)
        
        db.session.commit()
        print(f"✅ تم إضافة {len(sample_students)} طالبة تجريبية")

def test_bed_management():
    """اختبار إدارة الأسرة"""
    from models.core import add_bed_to_room, remove_bed_from_room
    
    app = create_app()
    
    with app.app_context():
        print("\n🧪 اختبار إدارة الأسرة...")
        
        # اختبار إضافة سرير
        room = Room.query.first()
        if room:
            print(f"الغرفة {room.room_code} تحتوي على {room.total_beds} أسرة")
            
            success, message = add_bed_to_room(room.id, 60.0)
            print(f"إضافة سرير: {message}")
            
            if success:
                room = Room.query.get(room.id)  # إعادة تحميل
                print(f"الآن تحتوي على {room.total_beds} أسرة")
                
                # عرض الأسرة الجديدة
                new_bed = Bed.query.filter_by(room_id=room.id).order_by(Bed.bed_number.desc()).first()
                if new_bed:
                    print(f"السرير الجديد: {new_bed.bed_code}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='إعداد نظام إدارة السكنات')
    parser.add_argument('--setup', action='store_true', help='إعداد قاعدة البيانات')
    parser.add_argument('--students', action='store_true', help='إضافة طالبات تجريبية')
    parser.add_argument('--test', action='store_true', help='اختبار إدارة الأسرة')
    parser.add_argument('--all', action='store_true', help='تنفيذ جميع العمليات')
    
    args = parser.parse_args()
    
    if args.all or args.setup:
        setup_database()
    
    if args.all or args.students:
        add_sample_students()
    
    if args.all or args.test:
        test_bed_management()
    
    if not any(vars(args).values()):
        print("استخدم --help لعرض الخيارات المتاحة")
        print("أو استخدم --all لتنفيذ جميع العمليات")

