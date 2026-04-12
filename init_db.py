"""
init_db.py — Initialize and seed the cable_tv_erp database.
Run: python init_db.py
"""

import os
import sys

# Allow imports from cable_tv_erp package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cable_tv_erp'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), 'cable_tv_erp', '.env'))

import mysql.connector
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

# --- SQL schema and seed data ---
SCHEMA_SQL = """
drop table if exists TransactionLine;
drop table if exists InventoryTransaction;
drop table if exists DeviceAssignment;
drop table if exists Device;
drop table if exists Item;
drop table if exists PaymentAllocation;
drop table if exists Payment;
drop table if exists InvoiceLineItem;
drop table if exists Invoice;
drop table if exists Subscription;
drop table if exists Package;
drop table if exists Ticket;
drop table if exists RoleHasPermission;
drop table if exists Permission;
drop table if exists Customer;
drop table if exists Employee;
drop table if exists Admin;
drop table if exists User;

create table User (
    userId int not null auto_increment,
    userName varchar(50) not null,
    passwordHash varchar(255) not null,
    status varchar(20) not null default 'active',
    primary key (userId),
    unique (userName)
);

insert into User values
(1,'admin_sara','hash_001','active'),(2,'admin_james','hash_002','active'),
(3,'admin_peter','hash_003','active'),(4,'admin_lisa','hash_004','active'),
(5,'admin_kevin','hash_005','active'),(6,'emp_mike','hash_006','active'),
(7,'emp_linda','hash_007','active'),(8,'emp_carlos','hash_008','active'),
(9,'emp_nina','hash_009','active'),(10,'emp_david','hash_010','active');

create table Admin (
    userId int not null,
    primary key (userId),
    foreign key (userId) references User(userId) on delete cascade
);
insert into Admin values (1),(2),(3),(4),(5);

create table Employee (
    userId int not null,
    primary key (userId),
    foreign key (userId) references User(userId) on delete cascade
);
insert into Employee values (6),(7),(8),(9),(10);

create table Customer (
    customerId int not null auto_increment,
    firstName varchar(50) not null,
    lastName varchar(50) not null,
    address varchar(255) not null,
    accountStatus varchar(20) not null default 'active',
    primary key (customerId)
);
insert into Customer (customerId, firstName, lastName, address, accountStatus) values
(11,'Alice','Smith','101 Maple St, Vancouver','active'),
(12,'Bob','Jones','202 Oak Ave, Burnaby','active'),
(13,'Charlie','Brown','303 Pine Rd, Surrey','active'),
(14,'Diana','Prince','404 Elm Blvd, Richmond','suspended'),
(15,'Evan','Wright','505 Cedar Ln, Coquitlam','active');

create table Permission (
    permissionCode varchar(50) not null,
    passwordId int not null,
    primary key (permissionCode)
);
insert into Permission values
('MANAGE_CUSTOMERS',1),('MANAGE_INVENTORY',2),('HANDLE_TICKETS',3),
('VIEW_REPORTS',4),('MANAGE_BILLING',5);

create table RoleHasPermission (
    userId int not null,
    permissionCode varchar(50) not null,
    primary key (userId, permissionCode),
    foreign key (userId) references User(userId) on delete cascade,
    foreign key (permissionCode) references Permission(permissionCode) on delete cascade
);
insert into RoleHasPermission values
(1,'MANAGE_CUSTOMERS'),(1,'MANAGE_BILLING'),(2,'VIEW_REPORTS'),
(2,'MANAGE_INVENTORY'),(3,'HANDLE_TICKETS'),(3,'MANAGE_CUSTOMERS'),
(4,'MANAGE_BILLING'),(5,'VIEW_REPORTS'),(6,'HANDLE_TICKETS'),
(7,'MANAGE_INVENTORY'),(8,'HANDLE_TICKETS'),(9,'VIEW_REPORTS'),
(10,'MANAGE_CUSTOMERS');

create table Ticket (
    ticketId int not null auto_increment,
    customerId int not null,
    handledBy int null,
    createdAt datetime not null default current_timestamp,
    priority varchar(20) not null,
    status varchar(20) not null default 'open',
    primary key (ticketId),
    foreign key (customerId) references Customer(customerId) on delete cascade,
    foreign key (handledBy) references Employee(userId) on delete set null
);
insert into Ticket values
(1,11,6,'2025-01-10 09:00:00','high','resolved'),
(2,12,7,'2025-01-15 10:30:00','medium','open'),
(3,13,8,'2025-02-01 11:00:00','low','open'),
(4,14,9,'2025-02-10 14:00:00','high','in-progress'),
(5,15,null,'2025-03-01 08:00:00','low','open');

create table Package (
    packageId int not null auto_increment,
    packageName varchar(100) not null,
    monthlyPrice decimal(10,2) not null,
    primary key (packageId),
    unique (packageName),
    check (monthlyPrice > 0)
);
insert into Package values
(1,'Basic',29.99),(2,'Standard',49.99),(3,'Premium',79.99),
(4,'Sports',59.99),(5,'Ultimate',99.99);

create table Subscription (
    subscriptionId int not null auto_increment,
    customerId int not null,
    packageId int not null,
    startDate date not null,
    endDate date null,
    status varchar(20) not null default 'active',
    primary key (subscriptionId),
    foreign key (customerId) references Customer(customerId) on delete cascade,
    foreign key (packageId) references Package(packageId) on delete restrict
);
insert into Subscription values
(1,11,1,'2024-01-01',null,'active'),(2,12,2,'2024-02-01',null,'active'),
(3,13,3,'2024-03-01',null,'active'),(4,14,4,'2024-01-15','2025-01-15','expired'),
(5,15,5,'2024-06-01',null,'active');

create table Invoice (
    invoiceId int not null auto_increment,
    customerId int not null,
    totalAmount decimal(10,2) not null,
    issueDate date not null,
    dueDate date not null,
    billingPeriod varchar(20) not null,
    invoiceStatus varchar(20) not null default 'unpaid',
    primary key (invoiceId),
    foreign key (customerId) references Customer(customerId) on delete cascade,
    check (totalAmount >= 0)
);
insert into Invoice values
(1,11,29.99,'2025-01-01','2025-01-15','JAN-2025','paid'),
(2,12,49.99,'2025-01-01','2025-01-15','JAN-2025','paid'),
(3,13,79.99,'2025-01-01','2025-01-15','JAN-2025','unpaid'),
(4,14,59.99,'2025-01-01','2025-01-15','JAN-2025','overdue'),
(5,15,99.99,'2025-01-01','2025-01-15','JAN-2025','paid');

create table InvoiceLineItem (
    invoiceId int not null,
    lineNumber int not null,
    subscriptionId int not null,
    description varchar(255) not null,
    unitPrice decimal(10,2) not null,
    unitCount int not null,
    primary key (invoiceId, lineNumber),
    foreign key (invoiceId) references Invoice(invoiceId) on delete cascade,
    foreign key (subscriptionId) references Subscription(subscriptionId) on delete restrict,
    check (unitPrice >= 0),
    check (unitCount > 0)
);
insert into InvoiceLineItem values
(1,1,1,'Basic Package - January 2025',29.99,1),
(2,1,2,'Standard Package - January 2025',49.99,1),
(3,1,3,'Premium Package - January 2025',79.99,1),
(4,1,4,'Sports Package - January 2025',59.99,1),
(5,1,5,'Ultimate Package - January 2025',99.99,1);

create table Payment (
    paymentId int not null auto_increment,
    customerId int not null,
    amount decimal(10,2) not null,
    paymentDate date not null,
    method varchar(50) not null,
    primary key (paymentId),
    foreign key (customerId) references Customer(customerId) on delete cascade,
    check (amount > 0)
);
insert into Payment values
(1,11,29.99,'2025-01-10','credit card'),(2,12,49.99,'2025-01-12','debit card'),
(3,13,40.00,'2025-01-14','bank transfer'),(4,15,99.99,'2025-01-13','credit card'),
(5,11,29.99,'2025-02-10','credit card');

create table PaymentAllocation (
    paymentId int not null,
    invoiceId int not null,
    allocatedAmount decimal(10,2) not null,
    primary key (paymentId, invoiceId),
    foreign key (paymentId) references Payment(paymentId) on delete cascade,
    foreign key (invoiceId) references Invoice(invoiceId) on delete cascade,
    check (allocatedAmount > 0)
);
insert into PaymentAllocation values
(1,1,29.99),(2,2,49.99),(3,3,40.00),(4,5,99.99),(5,1,29.99);

create table Item (
    itemId int not null auto_increment,
    itemName varchar(100) not null,
    category varchar(50) not null,
    primary key (itemId),
    unique (itemName)
);
insert into Item values
(1,'HD Set-Top Box','Device'),(2,'4K Set-Top Box','Device'),
(3,'Remote Control','Accessory'),(4,'HDMI Cable','Accessory'),
(5,'Signal Booster','Equipment');

create table Device (
    deviceId int not null auto_increment,
    itemId int not null,
    cardNumber varchar(50) not null,
    serialNumber varchar(50) not null,
    status varchar(20) not null default 'available',
    primary key (deviceId),
    foreign key (itemId) references Item(itemId) on delete restrict,
    unique (cardNumber),
    unique (serialNumber)
);
insert into Device values
(1,1,'CARD-1001','SN-A001','assigned'),(2,1,'CARD-1002','SN-A002','assigned'),
(3,2,'CARD-2001','SN-B001','assigned'),(4,2,'CARD-2002','SN-B002','available'),
(5,1,'CARD-1003','SN-A003','assigned');

create table DeviceAssignment (
    assignmentId int not null auto_increment,
    customerId int not null,
    deviceId int not null,
    assignedDate date not null,
    returnedDate date null,
    primary key (assignmentId),
    foreign key (customerId) references Customer(customerId) on delete cascade,
    foreign key (deviceId) references Device(deviceId) on delete restrict
);
insert into DeviceAssignment values
(1,11,1,'2024-01-01',null),(2,12,2,'2024-02-01',null),
(3,13,3,'2024-03-01',null),(4,14,4,'2024-01-15','2025-01-15'),
(5,15,5,'2024-06-01',null);

create table InventoryTransaction (
    transactionID int not null auto_increment,
    transactionType varchar(20) not null,
    transactionDate date not null,
    primary key (transactionID),
    check (transactionType in ('inbound','outbound'))
);
insert into InventoryTransaction values
(1,'inbound','2024-01-01'),(2,'inbound','2024-02-01'),
(3,'outbound','2024-03-01'),(4,'inbound','2024-04-01'),
(5,'outbound','2024-05-01');

create table TransactionLine (
    transactionID int not null,
    lineNumber int not null,
    itemId int not null,
    quantity int not null,
    primary key (transactionID, lineNumber),
    foreign key (transactionID) references InventoryTransaction(transactionID) on delete cascade,
    foreign key (itemId) references Item(itemId) on delete restrict,
    check (quantity > 0)
);
insert into TransactionLine values
(1,1,1,10),(1,2,2,5),(2,1,3,20),(3,1,1,3),(4,1,4,15);
"""


def main():
    print("Connecting to MySQL...")
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        autocommit=True
    )
    cursor = conn.cursor()

    # Create database if not exists
    print(f"Creating database '{DB_NAME}' if not exists...")
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor.execute(f"USE `{DB_NAME}`")

    # Run schema + seed SQL
    print("Running schema and seed SQL...")
    for statement in SCHEMA_SQL.split(';'):
        stmt = statement.strip()
        if stmt:
            cursor.execute(stmt)

    # Hash passwords with bcrypt
    print("Hashing passwords with bcrypt...")
    try:
        from flask_bcrypt import Bcrypt
        from flask import Flask
        app = Flask(__name__)
        bcrypt = Bcrypt(app)
    except ImportError:
        print("WARNING: flask-bcrypt not installed. Install with: pip install flask-bcrypt")
        print("Passwords will remain as plaintext hashes.")
        cursor.close()
        conn.close()
        print("Database initialized successfully.")
        return

    # Get all users
    cursor.execute("SELECT userId, userName FROM User")
    users = cursor.fetchall()

    with app.app_context():
        for user_id, user_name in users:
            password = f"{user_name}_pass"
            hashed = bcrypt.generate_password_hash(password).decode('utf-8')
            cursor.execute(
                "UPDATE User SET passwordHash = %s WHERE userId = %s",
                (hashed, user_id)
            )

    print(f"Hashed passwords for {len(users)} users.")
    print("  Example credentials:")
    print("    Admin:    admin_sara / admin_sara_pass")
    print("    Employee: emp_mike / emp_mike_pass")

    cursor.close()
    conn.close()
    print("Database initialized successfully.")


if __name__ == '__main__':
    main()
