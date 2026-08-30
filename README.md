# TICKETPASS/1.0 — Protocol สำหรับจองบัตรคอนเสิร์ต

ตัวอย่างโปรแกรมแบบ console เพื่อสาธิต application-layer protocol บน TCP สำหรับจองบัตรคอนเสิร์ตที่มีจำนวนจำกัด

## วิธีรันโปรแกรม

เปิด PowerShell สองหน้าต่างในโฟลเดอร์โปรเจกต์ แล้วรันคำสั่งต่อไปนี้:

```powershell
python server.py
python client.py
```

Server เริ่มต้นด้วยบัตร `VIP=5`, `A=20` และ `B=50` ใบ แต่ละการเชื่อมต่อจาก client จะส่งหนึ่ง request และรับหนึ่ง response จึงตรวจดูข้อความ protocol ด้วย Wireshark ได้ง่าย

## รูปแบบข้อความ Protocol

แต่ละข้อความใช้ UTF-8 และจบด้วยบรรทัดว่าง (`\r\n\r\n`):

```text
TICKETPASS/1.0 HOLD
Request-ID: REQ-01
User-ID: U-100
Zone: VIP
Quantity: 2
Hold-Seconds: 60

```

คำสั่งหลักคือ:

- `CHECK` — ตรวจสอบจำนวนบัตรที่ยังเหลือ
- `HOLD` — ล็อกบัตรไว้ชั่วคราว
- `CONFIRM` — ยืนยันการจอง
- `CANCEL` — ยกเลิกการจอง
- `STATUS` — ตรวจสอบสถานะการจอง

รหัสสถานะสำคัญ ได้แก่ `200 OK`, `201 HELD`, `400 BAD_REQUEST`, `404 NOT_FOUND`, `409 SOLD_OUT` และ `410 HOLD_EXPIRED`

## คุณลักษณะที่นำไปสาธิตได้

- **ป้องกันการจองเกินจำนวน:** Server ใช้ lock ขณะปรับจำนวนบัตร จึงไม่อนุญาตให้ client หลายคนล็อกบัตรเกินจำนวนที่มีจริง
- **การจองชั่วคราว:** บัตรสถานะ `HELD` จะถูกคืนเข้าระบบหลังครบเวลา `Hold-Seconds` หากไม่มีการยืนยัน
- **ป้องกันคำขอซ้ำ:** หากส่ง `HOLD` ซ้ำโดยใช้ `Request-ID` เดิม Server จะตอบผลลัพธ์เดิมและไม่ตัดบัตรเพิ่ม
- **สถานะชัดเจน:** การจองเปลี่ยนจาก `HELD → BOOKED` หรือ `HELD → CANCELLED/EXPIRED → AVAILABLE`

## การตรวจสอบด้วย Wireshark

เริ่ม capture ที่ interface Loopback แล้วใช้ Display Filter:

```text
tcp.port == 5050 && tcp.len > 0
```

เลือก packet ที่มี `PSH, ACK` แล้วคลิกขวา **Follow → TCP Stream** จะเห็นข้อความ request และ response ของ TICKETPASS/1.0 ที่ส่งจริง

## Link clip

```text
https://drive.google.com/file/d/1NzPcp58xMM9PMBALRLjuMMt-hw8ZumuS/view?usp=sharing
```