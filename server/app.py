"""Sentinel starter API. Configure a trusted identity provider before deployment."""
import json
import os
from datetime import date
from functools import wraps

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from flask_cors import CORS

load_dotenv()
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")}})
ROLES = {"admin", "base_commander", "logistics_officer"}


def db_connection():
    return mysql.connector.connect(
        host=os.environ["MYSQL_HOST"], port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.environ["MYSQL_USER"], password=os.environ["MYSQL_PASSWORD"],
        database=os.environ["MYSQL_DATABASE"], ssl_disabled=False,
        autocommit=False,
    )


def rows(sql, params=()):
    conn = db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        conn.close()


def authorized(*roles):
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            role = request.headers.get("X-User-Role", "")
            if role not in ROLES:
                return jsonify(error="Authentication required"), 401
            if roles and role not in roles:
                return jsonify(error="Insufficient permissions"), 403
            raw_user, raw_base = request.headers.get("X-User-Id"), request.headers.get("X-Base-Id")
            try:
                g.user_id = int(raw_user) if raw_user else None
                g.base_id = int(raw_base) if raw_base else None
            except ValueError:
                return jsonify(error="Invalid identity headers"), 401
            g.role = role
            return fn(*args, **kwargs)
        return wrapped
    return decorate


def scoped_base():
    if g.role == "admin":
        return request.args.get("baseId", type=int) or (request.get_json(silent=True) or {}).get("baseId")
    return g.base_id


def require_base(base_id):
    if not base_id:
        return jsonify(error="A base must be selected"), 400
    if g.role != "admin" and base_id != g.base_id:
        return jsonify(error="Access is limited to your assigned base"), 403
    return None


def audit(cur, action, entity, entity_id, base_id, after):
    cur.execute(
        "INSERT INTO audit_log(actor_id,action,entity_type,entity_id,base_id,after_data,request_id) VALUES(%s,%s,%s,%s,%s,%s,%s)",
        (g.user_id, action, entity, entity_id, base_id, json.dumps(after, default=str), request.headers.get("X-Request-Id")),
    )


def mutate(sql, values, action, entity, base_id):
    conn = db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, values)
        entity_id = cur.lastrowid
        cur.execute(f"SELECT * FROM {entity} WHERE id=%s", (entity_id,))
        record = cur.fetchone()
        audit(cur, action, entity, entity_id, base_id, record)
        conn.commit()
        return record
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@app.get("/api/health")
def health():
    try:
        rows("SELECT 1")
        return jsonify(status="ok", database="connected")
    except Exception:
        app.logger.exception("Database health check failed")
        return jsonify(status="error", database="unavailable"), 503


@app.get("/api/bases")
@authorized("admin", "base_commander", "logistics_officer")
def bases():
    if g.role == "admin":
        return jsonify(rows("SELECT id,name,code,location FROM bases ORDER BY name"))
    return jsonify(rows("SELECT id,name,code,location FROM bases WHERE id=%s", (g.base_id,)))


@app.get("/api/equipment")
@authorized("admin", "base_commander", "logistics_officer")
def equipment():
    base = scoped_base()
    return jsonify(rows("SELECT id,name,category,unit,reorder_level FROM equipment_types ORDER BY category,name"))


@app.get("/api/dashboard")
@authorized("admin", "base_commander", "logistics_officer")
def dashboard():
    base = scoped_base()
    start = request.args.get("from", "1900-01-01")
    end = request.args.get("to", date.today().isoformat())
    category = request.args.get("category")
    if base is None and g.role != "admin":
        return jsonify(error="No base is assigned to this account"), 400
    result = rows("""
      SELECT e.id,e.name,e.category,e.unit,
       (SELECT COALESCE(SUM(p.quantity),0) FROM purchases p WHERE p.equipment_type_id=e.id AND p.purchase_date < %s AND (%s IS NULL OR p.base_id=%s)) opening_purchases,
       (SELECT COALESCE(SUM(t.quantity),0) FROM transfers t WHERE t.equipment_type_id=e.id AND t.status='received' AND t.received_at < %s AND (%s IS NULL OR t.to_base_id=%s)) opening_transfer_in,
       (SELECT COALESCE(SUM(t.quantity),0) FROM transfers t WHERE t.equipment_type_id=e.id AND t.dispatched_at < %s AND t.status<>'cancelled' AND (%s IS NULL OR t.from_base_id=%s)) opening_transfer_out,
       (SELECT COALESCE(SUM(x.quantity),0) FROM expenditures x WHERE x.equipment_type_id=e.id AND x.expended_at < %s AND (%s IS NULL OR x.base_id=%s)) opening_expended,
       (SELECT COALESCE(SUM(p.quantity),0) FROM purchases p WHERE p.equipment_type_id=e.id AND p.purchase_date BETWEEN %s AND %s AND (%s IS NULL OR p.base_id=%s)) purchases,
       (SELECT COALESCE(SUM(t.quantity),0) FROM transfers t WHERE t.equipment_type_id=e.id AND t.status='received' AND DATE(t.received_at) BETWEEN %s AND %s AND (%s IS NULL OR t.to_base_id=%s)) transfer_in,
       (SELECT COALESCE(SUM(t.quantity),0) FROM transfers t WHERE t.equipment_type_id=e.id AND t.status<>'cancelled' AND DATE(t.dispatched_at) BETWEEN %s AND %s AND (%s IS NULL OR t.from_base_id=%s)) transfer_out,
       (SELECT COALESCE(SUM(a.quantity),0) FROM assignments a WHERE a.equipment_type_id=e.id AND a.returned_at IS NULL AND (%s IS NULL OR a.base_id=%s)) assigned,
       (SELECT COALESCE(SUM(x.quantity),0) FROM expenditures x WHERE x.equipment_type_id=e.id AND DATE(x.expended_at) BETWEEN %s AND %s AND (%s IS NULL OR x.base_id=%s)) expended
      FROM equipment_types e WHERE (%s IS NULL OR e.category=%s) ORDER BY e.category,e.name
    """, (start,base,base,start,base,base,start,base,base,start,base,base,
           start,end,base,base,start,end,base,base,start,end,base,base,
           base,base,start,end,base,base,category,category))
    for item in result:
        item["opening_balance"] = item.pop("opening_purchases") + item.pop("opening_transfer_in") - item.pop("opening_transfer_out") - item.pop("opening_expended")
        item["net_movement"] = item["purchases"] + item["transfer_in"] - item["transfer_out"]
        item["closing_balance"] = item["opening_balance"] + item["net_movement"] - item["expended"]
    return jsonify(result)


@app.get("/api/purchases")
@authorized("admin", "base_commander", "logistics_officer")
def get_purchases():
    base = scoped_base()
    return jsonify(rows("""SELECT p.*,b.name base,e.name equipment,e.category FROM purchases p JOIN bases b ON b.id=p.base_id JOIN equipment_types e ON e.id=p.equipment_type_id WHERE (%s IS NULL OR p.base_id=%s) AND (%s IS NULL OR p.purchase_date >= %s) AND (%s IS NULL OR p.purchase_date <= %s) AND (%s IS NULL OR p.equipment_type_id=%s) ORDER BY p.purchase_date DESC,p.id DESC""",
        (base,base,request.args.get("from"),request.args.get("from"),request.args.get("to"),request.args.get("to"),request.args.get("equipmentTypeId"),request.args.get("equipmentTypeId"))))


@app.post("/api/purchases")
@authorized("admin", "base_commander", "logistics_officer")
def create_purchase():
    data = request.get_json(silent=True) or {}
    base = scoped_base()
    denied = require_base(base)
    if denied: return denied
    try:
        quantity = int(data["quantity"])
        if quantity <= 0: raise ValueError()
        record = mutate("INSERT INTO purchases(base_id,equipment_type_id,quantity,purchase_date,reference,recorded_by) VALUES(%s,%s,%s,%s,%s,%s)",
            (base,int(data["equipmentTypeId"]),quantity,data["purchaseDate"],data.get("reference"),g.user_id),"purchase.recorded","purchases",base)
        return jsonify(record), 201
    except (KeyError, TypeError, ValueError): return jsonify(error="Valid equipmentTypeId, positive quantity, and purchaseDate are required"), 400


@app.get("/api/transfers")
@authorized("admin", "base_commander", "logistics_officer")
def get_transfers():
    base = scoped_base()
    return jsonify(rows("""SELECT t.*,fb.name from_base,tb.name to_base,e.name equipment,e.category FROM transfers t JOIN bases fb ON fb.id=t.from_base_id JOIN bases tb ON tb.id=t.to_base_id JOIN equipment_types e ON e.id=t.equipment_type_id WHERE (%s IS NULL OR t.from_base_id=%s OR t.to_base_id=%s) ORDER BY t.dispatched_at DESC""",(base,base,base)))


@app.post("/api/transfers")
@authorized("admin", "base_commander", "logistics_officer")
def create_transfer():
    data = request.get_json(silent=True) or {}
    try:
        source, destination = int(data["fromBaseId"]), int(data["toBaseId"])
        quantity = int(data["quantity"])
        if source == destination or quantity <= 0: raise ValueError()
    except (KeyError, TypeError, ValueError): return jsonify(error="Valid distinct bases and positive quantity are required"), 400
    if g.role != "admin" and source != g.base_id: return jsonify(error="Transfers must originate from your assigned base"), 403
    try:
        record = mutate("INSERT INTO transfers(from_base_id,to_base_id,equipment_type_id,quantity,reference,dispatched_by) VALUES(%s,%s,%s,%s,%s,%s)",
            (source,destination,int(data["equipmentTypeId"]),quantity,data["reference"],g.user_id),"transfer.dispatched","transfers",source)
        return jsonify(record), 201
    except (KeyError, TypeError, ValueError): return jsonify(error="A valid equipmentTypeId and reference are required"), 400


@app.post("/api/transfers/<int:transfer_id>/receive")
@authorized("admin", "base_commander")
def receive_transfer(transfer_id):
    conn = db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM transfers WHERE id=%s FOR UPDATE",(transfer_id,))
        transfer = cur.fetchone()
        if not transfer or transfer["status"] != "in_transit": conn.rollback(); return jsonify(error="Transfer unavailable for receiving"),404
        if g.role != "admin" and transfer["to_base_id"] != g.base_id: conn.rollback(); return jsonify(error="Only the destination base can receive this transfer"),403
        cur.execute("UPDATE transfers SET status='received',received_at=CURRENT_TIMESTAMP,received_by=%s WHERE id=%s",(g.user_id,transfer_id))
        transfer["status"]="received"
        audit(cur,"transfer.received","transfers",transfer_id,transfer["to_base_id"],transfer)
        conn.commit()
        return jsonify(transfer)
    except Exception:
        conn.rollback(); raise
    finally: conn.close()


@app.post("/api/assignments")
@authorized("admin", "base_commander")
def create_assignment():
    data=request.get_json(silent=True) or {}; base=scoped_base(); denied=require_base(base)
    if denied: return denied
    try:
        quantity=int(data["quantity"])
        if quantity<=0: raise ValueError()
        record=mutate("INSERT INTO assignments(base_id,equipment_type_id,quantity,personnel_name,unit_name,recorded_by) VALUES(%s,%s,%s,%s,%s,%s)",(base,int(data["equipmentTypeId"]),quantity,data["personnelName"],data.get("unitName"),g.user_id),"assignment.created","assignments",base)
        return jsonify(record),201
    except (KeyError,TypeError,ValueError): return jsonify(error="Valid equipment, positive quantity, and personnelName are required"),400


@app.post("/api/expenditures")
@authorized("admin", "base_commander")
def create_expenditure():
    data=request.get_json(silent=True) or {}; base=scoped_base(); denied=require_base(base)
    if denied: return denied
    try:
        quantity=int(data["quantity"])
        if quantity<=0: raise ValueError()
        record=mutate("INSERT INTO expenditures(base_id,equipment_type_id,quantity,purpose,reference,recorded_by) VALUES(%s,%s,%s,%s,%s,%s)",(base,int(data["equipmentTypeId"]),quantity,data.get("purpose"),data.get("reference"),g.user_id),"expenditure.recorded","expenditures",base)
        return jsonify(record),201
    except (KeyError,TypeError,ValueError): return jsonify(error="Valid equipmentTypeId and positive quantity are required"),400


@app.get("/api/audit")
@authorized("admin", "base_commander")
def get_audit():
    base=scoped_base()
    return jsonify(rows("SELECT * FROM audit_log WHERE (%s IS NULL OR base_id=%s) ORDER BY occurred_at DESC LIMIT 200",(base,base)))


@app.errorhandler(Exception)
def handle_error(error):
    app.logger.exception("API request failed", exc_info=error)
    return jsonify(error="Internal server error"),500


if __name__ == "__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT","4000")),debug=False)
