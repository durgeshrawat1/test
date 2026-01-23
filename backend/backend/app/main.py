import logging
import os
import base64
import json
import re
import ssl
import traceback
from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from pydantic import BaseModel, validator
from typing import List, Dict, Any
import csv
import io
import datetime
import decimal
from fastapi import UploadFile, File
from fastapi.responses import Response

# --- CONFIG ---
from . import config as _config

# Initialize logging early so we can log DB selection
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("banking-core")

# Determine DATABASE_URL safely.
DATABASE_URL = None
# For production deployments we do not enable any local-development fallbacks.
# Only honor an explicit DATABASE_URL environment variable or the configured
# pydantic settings value. Do not create or rely on local sqlite databases.
_env_db = os.getenv("DATABASE_URL")
if _env_db:
    DATABASE_URL = _env_db
else:
    DATABASE_URL = getattr(_config.settings, 'DATABASE_URL', None)

logger.info(f"Using DATABASE_URL={DATABASE_URL}")

# Extra diagnostic logs to help debug connection targets when starting the app.
try:
    logger.info(f"PWD={os.getcwd()}")
    logger.info(f"ENV DATABASE_URL={os.getenv('DATABASE_URL')}")
    # If pydantic settings are available, log their resolved components
    try:
        logger.info(f"settings.DB_HOST={getattr(_config.settings, 'DB_HOST', None)}")
        logger.info(f"settings.DATABASE_URL={getattr(_config.settings, 'DATABASE_URL', None)}")
    except Exception:
        logger.debug('Could not read _config.settings details')
except Exception:
    pass

# --- DATABASE SETUP ---
# PRESERVED: Your original local engine and SSL context initialization
engine = None
AsyncSessionLocal = None

if DATABASE_URL:
    try:
        # Do not allow sqlite-based DATABASE_URL in this production-only codepath.
        if 'sqlite' in DATABASE_URL:
            logger.error("SQLite DATABASE_URL detected — sqlite is not supported. Use a Postgres DATABASE_URL.")
            raise RuntimeError("sqlite DATABASE_URL is not supported; set a Postgres DATABASE_URL for production")

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        engine = create_async_engine(DATABASE_URL, echo=False, connect_args={"ssl": ctx})

        AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        logger.info("✅ Database Engine Configured")
    except Exception as e:
        logger.error(f"❌ Database Config Failed: {e}")




def meta_table(name: str) -> str:
    # Use the `system` schema for metadata tables in Postgres
    return f"system.{name}"


def phys_table(physical_name: str) -> str:
    # Reference physical data tables in the public schema
    return f"public.{physical_name}"

async def get_db():
    if AsyncSessionLocal is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    async with AsyncSessionLocal() as session:
        yield session

app = FastAPI(title="Data Nexus")



@app.on_event("startup")
async def run_migrations_on_startup():
    # Run migrations/init.sql if present to ensure metadata tables exist
    try:
        if engine is None:
            logger.warning('No DB engine available at startup; skipping migrations')
            return
        migrations_path = os.path.join(os.path.dirname(__file__), 'migrations', 'init.sql')
        if not os.path.exists(migrations_path):
            logger.info('No migrations/init.sql found; skipping')
            return
        # For Postgres, do not automatically run SQL init scripts unless explicitly requested
        apply_init = os.getenv('APPLY_INIT_SQL', 'false').lower() == 'true'
        if not apply_init:
            logger.info('Skipping migrations/init.sql for Postgres (set APPLY_INIT_SQL=true to run)')
        else:
            logger.info('Running migrations/init.sql')
            async with engine.begin() as conn:
                with open(migrations_path, 'r', encoding='utf-8') as f:
                    sql = f.read()
                # Split statements by semicolon and execute non-empty statements
                statements = [s.strip() for s in re.split(r';\s*\n', sql) if s.strip()]
                for stmt in statements:
                    try:
                        await conn.execute(text(stmt))
                    except Exception as e:
                        logger.debug(f'Ignoring migration statement error: {e}')
        logger.info('Migrations applied (if any)')
    except Exception as e:
        logger.error(f'Failed running migrations on startup: {e}')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- REQUEST SCHEMAS ---
class CreateDatasetRequest(BaseModel):
    name: str
    description: str
    accessGroup: str
    tableName: str
    # columns: list of {name: str, type: str, required: bool, validation: Optional[str]}
    columns: List[Dict[str, Any]]

    @validator('tableName')
    def validate_table_name(cls, v):
        if not re.match(r'^[a-zA-Z0-9_ ]+$', v):
            raise ValueError('Table name contains invalid characters')
        return v.strip().replace(" ", "_").lower()

    @validator('columns')
    def validate_columns(cls, v):
        if not isinstance(v, list) or len(v) == 0:
            raise ValueError('At least one column must be provided')
        for c in v:
            if 'name' not in c or 'type' not in c:
                raise ValueError('Each column requires a name and type')
            if not re.match(r'^[a-zA-Z0-9_]+$', c['name']):
                raise ValueError(f"Invalid column name: {c['name']}")
        return v

class CreateRecordRequest(BaseModel):
    data: Dict[str, Any]

# --- AUTH HELPERS ---
# PRESERVED: Your original robust JWT decoding and merging logic
def decode_jwt(token):
    if not token or token == "": return {}
    try:
        parts = token.split('.')
        if len(parts) < 2: return {}
        payload = parts[1]
        payload += '=' * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception as e:
        logger.error(f"JWT Decode Error: {e}")
        return {}

async def get_current_user(request: Request):
    # Read primary ALB headers and Authorization header first (backwards-compatible)
    h_data = request.headers.get('x-amzn-oidc-data')
    h_access = request.headers.get('x-amzn-oidc-accesstoken')
    h_auth = request.headers.get('authorization')

    claims: Dict[str, Any] = {}

    # Try the common headers first
    if h_data:
        claims.update(decode_jwt(h_data))
    if h_access:
        claims.update(decode_jwt(h_access))
    # Support Authorization: Bearer <token> from frontends or proxies
    if h_auth and isinstance(h_auth, str) and h_auth.lower().startswith('bearer '):
        try:
            token = h_auth.split(None, 1)[1]
            claims.update(decode_jwt(token))
        except Exception:
            logger.debug('Failed to decode Authorization bearer token')

    # Additionally scan all headers for any OIDC/JWT-like payloads that may contain groups
    # This helps cover ALB/Proxy variations which may forward different header names.
    scanned = []
    # Keywords to identify headers that may contain tokens/claims
    header_keywords = ('x-amzn-oidc', 'oidc', 'idtoken', 'accesstoken', 'jwt', 'cognito', 'x-user', 'x-auth')
    for name, val in request.headers.items():
        lname = name.lower()
        # skip Authorization (already handled) and obvious non-token headers
        if lname == 'authorization':
            continue
        if not any(k in lname for k in header_keywords):
            continue

        if not val:
            continue

        # Try splitting header values into candidate tokens (space/comma/semicolon separated)
        parts = re.split(r'[\s,;]+', val)
        for part in parts:
            if not part:
                continue
            # If looks like a JWT (has two dots) attempt to decode
            if part.count('.') >= 2:
                try:
                    d = decode_jwt(part)
                    if d:
                        claims.update(d)
                        scanned.append(name)
                        # continue to next header
                        break
                except Exception:
                    pass
            else:
                # Otherwise try to decode as base64-encoded JSON block
                try:
                    padded = part + '=' * (-len(part) % 4)
                    maybe_json = json.loads(base64.urlsafe_b64decode(padded))
                    if isinstance(maybe_json, dict):
                        claims.update(maybe_json)
                        scanned.append(name)
                        break
                except Exception:
                    # not base64/json - skip
                    pass

    if not claims:
        logger.warning("No claims found in ALB headers after scanning all OIDC-like headers")
        # In production, require real authentication claims.
        raise HTTPException(status_code=401)

    email = claims.get('email') or claims.get('upn') or claims.get('username') or 'unknown'

    # Collect groups from any common claim keys
    groups = (
        claims.get('cognito:groups')
        or claims.get('groups')
        or claims.get('roles')
        or claims.get('custom.groups')
        or claims.get('custom:groups')
        or claims.get('group')
        or []
    )
    # Normalize string/list formats and split comma/semicolon-separated strings
    if isinstance(groups, str):
        groups = [g.strip() for g in re.split(r'[;,]', groups) if g.strip()]

    # If scanning merged additional claim sources, try to pick up groups from nested structures
    if not groups:
        # Some providers include groups under a nested claim like 'realm_access': { 'roles': [...] }
        ra = claims.get('realm_access')
        if isinstance(ra, dict):
            rroles = ra.get('roles')
            if isinstance(rroles, list):
                groups = rroles

    # Ensure groups is a list of trimmed strings
    try:
        groups = [str(g).strip() for g in (groups or []) if g is not None]
    except Exception:
        groups = []

    logger.info(f"User {email} groups resolved: {groups} (scanned headers: {scanned})")

    return {
        "id": claims.get('sub') or claims.get('oid'),
        "email": email,
        "name": email.split('@')[0].capitalize(),
        "groups": groups
    }


def _parse_datetime_string(s: Any) -> datetime.datetime:
    """Parse a wide range of datetime string formats into a datetime object.
    Accepts datetime/date objects and numeric epoch seconds as well.
    Raises ValueError on failure.
    """
    if s is None:
        raise ValueError('None is not a datetime')
    if isinstance(s, datetime.datetime):
        return s
    if isinstance(s, datetime.date) and not isinstance(s, datetime.datetime):
        return datetime.datetime.combine(s, datetime.time.min)

    st = str(s).strip()
    # common trailing Z (UTC) -> make ISO compatible for fromisoformat
    if st.endswith('Z'):
        st = st[:-1] + '+00:00'

    # Try fromisoformat first (fast path)
    try:
        return datetime.datetime.fromisoformat(st)
    except Exception:
        pass

    # Try a set of common formats (with and without fractional seconds)
    fmts = (
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%d',
        '%Y/%m/%d %H:%M:%S',
        '%d-%m-%Y %H:%M:%S',
    )
    for f in fmts:
        try:
            dt = datetime.datetime.strptime(st, f)
            return dt
        except Exception:
            continue

    # Try parsing as epoch seconds
    try:
        if re.match(r'^\d{10}(?:\.\d+)?$', st):
            return datetime.datetime.fromtimestamp(float(st))
    except Exception:
        pass

    # As a last resort, try dateutil if available (optional dependency)
    try:
        from dateutil import parser as _dparser
        return _dparser.parse(st)
    except Exception:
        pass

    raise ValueError('invalid datetime format')


def _validate_and_coerce_row(row: Dict[str, Any], cols: Dict[str, Dict[str, Any]], *, enforce_required: bool = True):
    """
    Validate and coerce a single row (dict) according to `cols` metadata.
    `cols` is a mapping: column_name -> {data_type, required, validation}
    Returns: (params: dict, keys: List[str])
    Raises HTTPException(400) on validation failure.
    """
    params = {}
    keys = []

    for k, raw in row.items():
        if k not in cols:
            # ignore unknown columns
            continue

        meta_col = cols[k]
        v = raw
        if isinstance(v, str):
            v = v.strip()
            if v == '':
                v = None

        if enforce_required and meta_col.get('required') and (v is None):
            raise HTTPException(status_code=400, detail=f"{k} is required")

        if v is not None:
            # Normalize data_type and allow substring matches for Postgres variants
            raw_dt = meta_col.get('data_type')
            dt = (raw_dt or '').lower()
            # Fallback heuristics when data_type is missing or appears textual:
            # treat *_at and fields containing 'date' as timestamps/dates so they get coerced.
            if not dt or any(tok in dt for tok in ('text', 'string', 'char', 'varchar')):
                if k.endswith('_at') or 'date' in k:
                    dt = 'timestamp'
            try:
                if dt == 'int' or dt.startswith('int'):
                    params[k] = int(v)
                elif dt == 'float' or dt.startswith('float') or dt.startswith('numeric') or dt.startswith('decimal'):
                    params[k] = float(v)
                elif dt in ('text', 'string') or dt.startswith('varchar') or dt.startswith('char'):
                    params[k] = str(v)
                elif 'timestamp' in dt or 'datetime' in dt or 'timestamptz' in dt:
                    # Accept ISO formats and common SQL datetimes like 'YYYY-MM-DD HH:MM:SS'
                    try:
                        parsed = _parse_datetime_string(v)
                        params[k] = parsed
                    except HTTPException:
                        raise
                    except Exception as e:
                        raise ValueError(f'invalid datetime format: {e}')
                elif 'date' == dt or (('date' in dt) and ('timestamp' not in dt)):
                    if isinstance(v, datetime.date) and not isinstance(v, datetime.datetime):
                        params[k] = v
                    else:
                        s = str(v)
                        parsed = None
                        try:
                            parsed = datetime.date.fromisoformat(s)
                        except Exception:
                            try:
                                parsed = datetime.datetime.strptime(s, '%Y-%m-%d').date()
                            except Exception:
                                parsed = None
                        if parsed is None:
                            raise ValueError('invalid date format')
                        params[k] = parsed
                elif dt == 'bool' or dt.startswith('bool'):
                    if isinstance(v, bool):
                        params[k] = v
                    elif str(v).lower() in ('true', '1', 'yes'):
                        params[k] = True
                    elif str(v).lower() in ('false', '0', 'no'):
                        params[k] = False
                    else:
                        raise ValueError('invalid boolean')
                else:
                    params[k] = str(v)
            except HTTPException:
                raise
            except Exception as ex:
                logger.error(f"Coercion failed for column '{k}' expected '{meta_col.get('data_type')}' value '{v}': {ex}")
                raise HTTPException(status_code=400, detail=f"{k} has invalid type for {meta_col.get('data_type')}: {ex}")

            # additional validations
            if meta_col.get('validation') == 'full_name' and re.search(r'\d', str(v)):
                raise HTTPException(status_code=400, detail=f"{k} appears invalid (no digits allowed)")
            if meta_col.get('validation') == 'email' and not re.match(r'^\S+@\S+\.\S+$', str(v)):
                raise HTTPException(status_code=400, detail=f"{k} must be a valid email")
        else:
            params[k] = None

        keys.append(k)

    if not keys:
        raise HTTPException(status_code=400, detail='No valid columns provided')

    return params, keys

# --- ENDPOINTS ---

@app.get("/healthz")
async def health():
    return {"status": "ok"}


@app.get("/api/auth/me")
async def auth_me(request: Request):
    """Return the current authenticated user info derived from ALB/Cognito headers.
    This is a lightweight endpoint used by the frontend to detect session and groups.
    """
    try:
        user = await get_current_user(request)
        return {"user": user}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"auth_me error: {e}")
        raise HTTPException(status_code=500, detail="Internal error")

@app.get("/api/schemas")
async def get_schemas(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    try:
        u_groups = user.get('groups', [])
        # normalized lower-case set for case-insensitive comparisons
        u_groups_l = set([str(g).strip().lower() for g in u_groups if g])
        is_admin = any(str(g).upper() == "ADMIN" for g in u_groups)

        sql = f"SELECT id, name, description, access_group, physical_table_name FROM {meta_table('schemas')}"
        result = await db.execute(text(sql))
        rows = result.fetchall()

        return [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "accessGroup": r.access_group,
                "physical_table_name": r.physical_table_name,
            }
            for r in rows if is_admin or (isinstance(r.access_group, str) and r.access_group.strip().lower() in u_groups_l)
        ]
    except Exception as e:
        logger.error(f"DATABASE CRASH in get_schemas: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/admin/schema/{schema_id}")
async def delete_dataset(schema_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    if not any(str(g).upper() == "ADMIN" for g in user.get('groups', [])):
        raise HTTPException(status_code=403, detail="Admin access required")
    try:
        res = await db.execute(text(f"SELECT physical_table_name FROM {meta_table('schemas')} WHERE id = :id"), {"id": schema_id})
        meta = res.fetchone()
        if not meta: raise HTTPException(status_code=404, detail="Dataset not found")
        
        await db.execute(text(f"DELETE FROM {meta_table('schemas')} WHERE id = :id"), {"id": schema_id})
        drop_sql = f"DROP TABLE IF EXISTS {phys_table(meta.physical_table_name)} CASCADE"
        await db.execute(text(drop_sql))
        await db.commit()
        return {"status": "success"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/data/{schema_id}")
async def get_data(schema_id: int, limit: int = 25, offset: int = 0, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    try:
        # Resolve schema metadata
        res = await db.execute(text(f"SELECT physical_table_name, access_group FROM {meta_table('schemas')} WHERE id=:id"), {"id": schema_id})
        meta = res.fetchone()
        if not meta:
            raise HTTPException(status_code=404, detail="Schema not found")

        # Permission check
        u_groups = user.get('groups', [])
        u_groups_l = set([str(g).strip().lower() for g in u_groups if g])
        if not any(str(g).upper() == "ADMIN" for g in u_groups) and not (isinstance(meta.access_group, str) and meta.access_group.strip().lower() in u_groups_l):
            raise HTTPException(status_code=403)

        phys = phys_table(meta.physical_table_name)

        # Total count (efficient aggregate)
        count_res = await db.execute(text(f"SELECT COUNT(1) FROM {phys}"))
        total = int(count_res.scalar() or 0)

        # Fetch requested page
        query = text(f"SELECT * FROM {phys} ORDER BY id DESC LIMIT :limit OFFSET :offset")
        rows_res = await db.execute(query, {"limit": int(limit), "offset": int(offset)})
        fetched = rows_res.fetchall()
        # Convert SQLAlchemy Row objects to plain dicts via Row._mapping for stability across DB drivers
        rows = [dict(getattr(r, '_mapping', r)) if not isinstance(r, dict) else r for r in fetched]

        return {"rows": rows, "total": total}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/data/{schema_id}")
async def add_record(schema_id: int, req: CreateRecordRequest, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    # Fetch schema metadata once
    res = await db.execute(text(f"SELECT id, physical_table_name, access_group FROM {meta_table('schemas')} WHERE id=:id"), {"id": schema_id})
    meta = res.fetchone()
    if not meta:
        logger.warning(f"add_record: schema {schema_id} not found")
        raise HTTPException(status_code=404, detail="Schema not found")

    # Permission check
    u_groups = user.get('groups', [])
    u_groups_l = set([str(g).strip().lower() for g in u_groups if g])
    if not any(str(g).upper() == "ADMIN" for g in u_groups) and not (isinstance(meta.access_group, str) and meta.access_group.strip().lower() in u_groups_l):
        logger.warning(f"add_record: user {user.get('email')} unauthorized for schema {schema_id} (group {meta.access_group})")
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Server-side validation using system.table_columns
    try:
        colres = await db.execute(text(f"SELECT column_name, data_type, required, validation FROM {meta_table('table_columns')} WHERE schema_id = :id"), {"id": schema_id})
        cols = {r.column_name: {"data_type": r.data_type, "required": r.required, "validation": r.validation} for r in colres.fetchall()}

        # Filter incoming keys to allowed column names and safe identifier format
        incoming = {k: v for k, v in req.data.items() if re.match(r'^[a-z0-9_]+$', k) and k in cols}

        params, insert_keys = _validate_and_coerce_row(incoming, cols, enforce_required=True)

        columns_sql = ", ".join(insert_keys)
        placeholders = ", ".join([f":{k}" for k in insert_keys])
        insert_sql = text(f"INSERT INTO {phys_table(meta.physical_table_name)} ({columns_sql}) VALUES ({placeholders})")
        logger.info(f"add_record: inserting into {meta.physical_table_name} columns {insert_keys}")
        await db.execute(insert_sql, params)
        await db.commit()
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"add_record error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Database error")


@app.get("/api/data/{schema_id}/export-csv")
async def export_csv(schema_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    try:
        # Resolve schema metadata
        res = await db.execute(text(f"SELECT physical_table_name, access_group FROM {meta_table('schemas')} WHERE id=:id"), {"id": schema_id})
        meta = res.fetchone()
        if not meta:
            raise HTTPException(status_code=404, detail="Schema not found")

        # Permission check
        u_groups = user.get('groups', [])
        if not any(str(g).upper() == "ADMIN" for g in u_groups) and meta.access_group not in u_groups:
            raise HTTPException(status_code=403)

        phys = phys_table(meta.physical_table_name)

        # Stream rows in pages to avoid loading entire table into memory
        async def row_generator(page_size: int = 1000):
            offset = 0
            first = True
            while True:
                q = text(f"SELECT * FROM {phys} ORDER BY id DESC LIMIT :limit OFFSET :offset")
                r = await db.execute(q, {"limit": page_size, "offset": offset})
                chunk = r.fetchall()
                if not chunk:
                    break
                for row in chunk:
                    mapping = dict(getattr(row, '_mapping', row)) if not isinstance(row, dict) else row
                    if first:
                        out = io.StringIO()
                        writer = csv.writer(out)
                        writer.writerow(list(mapping.keys()))
                        yield out.getvalue().encode('utf-8')
                        first = False
                    out = io.StringIO()
                    writer = csv.writer(out)
                    writer.writerow([mapping.get(k) for k in mapping.keys()])
                    yield out.getvalue().encode('utf-8')
                offset += page_size

        filename = f"schema_{schema_id}.csv"
        headers = { 'Content-Disposition': f'attachment; filename="{filename}"' }
        from fastapi.responses import StreamingResponse
        return StreamingResponse(row_generator(), media_type='text/csv', headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"export_csv error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/data/{schema_id}/import-csv")
async def import_csv(schema_id: int, file: UploadFile = File(...), db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    try:
        # Resolve schema metadata
        res = await db.execute(text(f"SELECT physical_table_name, access_group FROM {meta_table('schemas')} WHERE id=:id"), {"id": schema_id})
        meta = res.fetchone()
        if not meta:
            raise HTTPException(status_code=404, detail="Schema not found")

        # Permission check - require Admin or group membership
        u_groups = user.get('groups', [])
        if not any(str(g).upper() == "ADMIN" for g in u_groups) and meta.access_group not in u_groups:
            raise HTTPException(status_code=403)

        # Read uploaded CSV and validate/coerce types per column metadata
        data = await file.read()
        text_data = data.decode('utf-8')
        reader = csv.DictReader(io.StringIO(text_data))
        rows = list(reader)
        if not rows:
            raise HTTPException(status_code=400, detail="CSV contains no rows")

        # Get columns metadata (name, data_type, required, validation)
        colres = await db.execute(text(f"SELECT column_name, data_type, required, validation FROM {meta_table('table_columns')} WHERE schema_id = :id"), {"id": schema_id})
        cols = {r.column_name: {"data_type": r.data_type, "required": r.required, "validation": r.validation} for r in colres.fetchall()}
        logger.info(f"Import CSV schema columns for schema_id={schema_id}: {cols}")
        if not cols:
            raise HTTPException(status_code=400, detail="Schema has no defined columns")

        # Robust header mapping: normalize CSV headers and map case-insensitively to defined cols
        # reader.fieldnames may contain original header strings; build mapping original_header -> col_name
        fieldnames = getattr(reader, 'fieldnames', None) or (list(rows[0].keys()) if rows else [])
        # normalization: lowercase, replace non-alnum/_ with underscore, strip surrounding underscores
        def _norm(h: str) -> str:
            if h is None:
                return ''
            s = h.replace('\ufeff', '').strip().lower()
            s = re.sub(r'[^a-z0-9_]+', '_', s)
            s = s.strip('_')
            return s

        header_to_col = {}
        for h in fieldnames:
            nh = _norm(h)
            if nh in cols:
                header_to_col[h] = nh

        insert_keys_candidate = list(dict.fromkeys(header_to_col.values()))
        if not insert_keys_candidate:
            # Provide helpful debug message listing detected headers and available columns
            detected = [str(h) for h in fieldnames]
            expected = list(cols.keys())
            raise HTTPException(status_code=400, detail=f"No valid columns in CSV to import. Detected headers: {detected}. Expected columns: {expected}")

        inserted = 0
        # Use a fresh transaction/connection for bulk inserts to avoid "transaction already begun" on session
        async with engine.begin() as conn:
            for idx, row in enumerate(rows):
                # Build incoming map using mapped column names -> CSV cell values
                incoming = {col: row.get(h) for h, col in header_to_col.items()}
                logger.info(f"Import CSV row[{idx}] incoming raw: {incoming}")
                try:
                    logger.info(f"Import CSV row[{idx}] meta subset: {[ (k, cols.get(k)) for k in incoming.keys() ]}")
                except Exception:
                    logger.debug('Could not log meta subset for import row')
                try:
                    params, keys = _validate_and_coerce_row(incoming, cols, enforce_required=True)
                except HTTPException as he:
                    # Validation failed for this row - include context
                    logger.error(f"Validation failed on CSV row {idx}: {he.detail} -- incoming: {incoming}")
                    raise
                except Exception as ex:
                    logger.error(f"Unexpected error validating CSV row {idx}: {ex} -- incoming: {incoming}")
                    raise
                columns_sql = ", ".join(keys)
                placeholders = ", ".join([f":{k}" for k in keys])
                insert_sql = text(f"INSERT INTO {phys_table(meta.physical_table_name)} ({columns_sql}) VALUES ({placeholders})")
                # Debug: log param types before execution to help diagnose asyncpg binding errors
                try:
                    logger.info(f"Import executing row {idx} param types: {[ (k, type(v).__name__) for k,v in params.items() ]}")
                except Exception:
                    logger.debug('Could not enumerate param types for import row')
                await conn.execute(insert_sql, params)
                inserted += 1

        return {"status": "success", "inserted": inserted}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"import_csv error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/data/{schema_id}/{record_id}")
async def update_record(schema_id: int, record_id: int, req: CreateRecordRequest, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    # 1. Verify Schema & Permissions
    res = await db.execute(text(f"SELECT physical_table_name, access_group FROM {meta_table('schemas')} WHERE id=:id"), {"id": schema_id})
    meta = res.fetchone()
    if not meta: raise HTTPException(404, detail="Schema not found")
    
    # Permission Check (Admin OR Group Match)
    u_groups = user.get('groups', [])
    u_groups_l = set([str(g).strip().lower() for g in u_groups if g])
    if not any(str(g).upper() == "ADMIN" for g in u_groups) and not (isinstance(meta.access_group, str) and meta.access_group.strip().lower() in u_groups_l):
        raise HTTPException(status_code=403, detail="Unauthorized")

    # 2. Construct Dynamic Update
    # EXCLUDE immutable fields like 'id' by default. Allow Admins to update `created_at`.
    is_admin = any(str(g).upper() == "ADMIN" for g in user.get('groups', []))
    immutable_fields = {'id'}
    if not is_admin:
        immutable_fields.add('created_at')
    incoming = {k: v for k, v in req.data.items() if k not in immutable_fields and re.match(r'^[a-z0-9_]+$', k)}

    if not incoming:
        raise HTTPException(status_code=400, detail="No valid updatable fields provided")

    try:
        # load columns metadata and coerce values (do not enforce required fields for updates)
        colres = await db.execute(text(f"SELECT column_name, data_type, required, validation FROM {meta_table('table_columns')} WHERE schema_id = :id"), {"id": schema_id})
        cols = {r.column_name: {"data_type": r.data_type, "required": r.required, "validation": r.validation} for r in colres.fetchall()}

        logger.info(f"Update incoming data: {incoming}")
        logger.info(f"Update columns metadata: {list(cols.items())}")
        try:
            params_coerced, valid_keys = _validate_and_coerce_row(incoming, cols, enforce_required=False)
        except HTTPException as he:
            logger.error(f"Validation error during update: {he.detail}")
            raise
        except Exception as ex:
            logger.error(f"Unexpected validation exception during update: {ex}")
            raise
        if not valid_keys:
            raise HTTPException(status_code=400, detail="No valid columns to update")

        set_clause = ", ".join([f"{k}=:{k}" for k in valid_keys])
        # Use RETURNING to get the updated row back and avoid racey reads
        query = text(f"UPDATE {phys_table(meta.physical_table_name)} SET {set_clause} WHERE id=:rid RETURNING *")
        params = {**params_coerced, "rid": record_id}

        logger.info(f"Executing UPDATE on {meta.physical_table_name} for ID {record_id} with keys {valid_keys}")
        try:
            logger.info(f"Update executing param types: {[ (k, type(v).__name__) for k,v in params.items() ]}")
        except Exception:
            logger.debug('Could not enumerate update param types')

        result = await db.execute(query, params)
        updated = result.fetchone()
        await db.commit()

        logger.info(f"UPDATE returned row: {updated}")

        if not updated:
            raise HTTPException(status_code=404, detail="Record not found")

        # Convert to mapping and make JSON-serializable for response
        try:
            mapping = dict(getattr(updated, '_mapping', updated)) if updated is not None else None
            logger.info(f"Post-update row mapping for id={record_id}: {mapping}")
        except Exception:
            logger.debug('Could not convert updated row to mapping')
            mapping = None

        serializable = {}
        if mapping is not None:
            for k, v in mapping.items():
                try:
                    if isinstance(v, decimal.Decimal):
                        # convert Decimal to float to keep numeric semantics
                        serializable[k] = float(v)
                    elif isinstance(v, (datetime.datetime, datetime.date)):
                        serializable[k] = v.isoformat()
                    elif isinstance(v, bytes):
                        try:
                            serializable[k] = v.decode('utf-8')
                        except Exception:
                            serializable[k] = str(v)
                    else:
                        # ensure JSON encodable
                        try:
                            json.dumps(v)
                            serializable[k] = v
                        except Exception:
                            serializable[k] = str(v)
                except Exception:
                    serializable[k] = str(v)

        return {"status": "success", "updated": serializable}
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Update failed for table {meta.physical_table_name} ID {record_id}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Database update error: {str(e)}")

@app.post("/api/data/{schema_id}/import")
async def import_data(schema_id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    # payload: { rows: [ {col: val} ] }
    res = await db.execute(text(f"SELECT physical_table_name, access_group FROM {meta_table('schemas')} WHERE id=:id"), {"id": schema_id})
    meta = res.fetchone()
    if not meta: raise HTTPException(404)
    u_groups = user.get('groups', [])
    u_groups_l = set([str(g).strip().lower() for g in u_groups if g])
    if not any(str(g).upper() == "ADMIN" for g in u_groups) and not (isinstance(meta.access_group, str) and meta.access_group.strip().lower() in u_groups_l):
        raise HTTPException(status_code=403)

    rows = payload.get('rows', [])
    if not isinstance(rows, list) or len(rows) == 0:
        raise HTTPException(status_code=400, detail='No rows provided')

    # load columns metadata
    colres = await db.execute(text(f"SELECT column_name, data_type, required, validation FROM {meta_table('table_columns')} WHERE schema_id = :id"), {"id": schema_id})
    cols = {r.column_name: {"data_type": r.data_type, "required": r.required, "validation": r.validation} for r in colres.fetchall()}

    inserted = 0
    errors = []
    try:
        async with db.begin():
            for idx, row in enumerate(rows):
                try:
                    # Filter to known columns
                    incoming = {k: v for k, v in row.items() if k in cols}
                    params, keys = _validate_and_coerce_row(incoming, cols, enforce_required=True)
                    columns_sql = ", ".join(keys)
                    placeholders = ", ".join([f":{k}" for k in keys])
                    await db.execute(text(f"INSERT INTO {phys_table(meta.physical_table_name)} ({columns_sql}) VALUES ({placeholders})"), params)
                    inserted += 1
                except Exception as e:
                    errors.append({"row": idx, "error": str(e)})
        return {"status": "completed", "inserted": inserted, "errors": errors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Add this to your main.py ---
# This fixes the 404 error you are seeing in the logs

@app.get("/api/metadata/tables")
async def get_metadata_tables(group: str, limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    try:
        u_groups = user.get('groups', [])
        u_groups_l = set([str(g).strip().lower() for g in u_groups if g])
        is_admin = any(str(g).upper() == "ADMIN" for g in u_groups)

        # 1. SECURITY: Admin bypass or exact group match (case-insensitive). Admins may query any group dynamically.
        if not is_admin and group.strip().lower() not in u_groups_l:
            logger.warning(f"Unauthorized metadata access attempt by {user['email']} for group {group}")
            raise HTTPException(status_code=403, detail="Unauthorized for this group")

        # 2. DATABASE QUERY:
        # For admins we support prefix matching (case-insensitive) so queries can match groups by prefix.
        # Build base query based on admin vs regular user
        if is_admin:
            # Postgres supports ILIKE for case-insensitive prefix matching
            where_clause = "access_group ILIKE :g"
            params = {"g": f"{group}%"}
        else:
            # force case-insensitive match by lowering access_group in SQL
            where_clause = "LOWER(access_group) = :g"
            params = {"g": group.strip().lower()}

        # Count total
        count_q = text(f"SELECT COUNT(1) FROM {meta_table('schemas')} WHERE {where_clause}")
        count_res = await db.execute(count_q, params)
        total = int(count_res.scalar() or 0)

        # Fetch page
        page_q = text(f"SELECT id, name, description, physical_table_name FROM {meta_table('schemas')} WHERE {where_clause} ORDER BY name LIMIT :limit OFFSET :offset")
        page_params = {**params, "limit": int(limit), "offset": int(offset)}
        result = await db.execute(page_q, page_params)
        rows = result.fetchall()

        logger.info(f"Metadata match for group '{group}': returning {len(rows)} of {total} tables")

        items = [{"id": r.id, "name": r.name, "description": r.description, "physical_table_name": r.physical_table_name} for r in rows]
        return {"items": items, "total": total}
    except Exception as e:
        logger.error(f"Metadata Error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metadata/schemas-search")
async def search_schemas(q: str | None = None, limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Search schemas by name (case-insensitive, prefix or substring) with pagination.
    Respects admin vs regular user permissions.
    """
    try:
        u_groups = user.get('groups', [])
        is_admin = any(str(g).upper() == 'ADMIN' for g in u_groups)

        base_where = []
        params: Dict[str, Any] = {}

        if q:
            # Use ILIKE with surrounding `%` for substring match
            base_where.append("name ILIKE :q")
            params['q'] = f"%{q}%"

        if not is_admin:
            # restrict to user's groups (case-insensitive)
            base_where.append("LOWER(access_group) = ANY(:g)")
            params['g'] = [str(g).strip().lower() for g in u_groups]

        where_clause = (' AND '.join(base_where)) if base_where else 'TRUE'

        count_q = text(f"SELECT COUNT(1) FROM {meta_table('schemas')} WHERE {where_clause}")
        total = int((await db.execute(count_q, params)).scalar() or 0)

        page_q = text(f"SELECT id, name, description, access_group, physical_table_name FROM {meta_table('schemas')} WHERE {where_clause} ORDER BY name LIMIT :limit OFFSET :offset")
        params.update({"limit": int(limit), "offset": int(offset)})
        res = await db.execute(page_q, params)
        rows = res.fetchall()

        items = [{"id": r.id, "name": r.name, "description": r.description, "access_group": r.access_group, "physical_table_name": r.physical_table_name} for r in rows]
        return {"items": items, "total": total}
    except Exception as e:
        logger.error(f"search_schemas error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metadata/groups")
async def get_metadata_groups(limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    try:
        u_groups = user.get('groups', [])
        u_groups_l = set([str(g).strip().lower() for g in u_groups if g])
        is_admin = any(str(g).upper() == "ADMIN" for g in u_groups)

        # If not admin, restrict groups to those the user belongs to
        if is_admin:
            count_q = text(f"SELECT COUNT(1) FROM (SELECT access_group FROM {meta_table('schemas')} GROUP BY access_group) as g")
            res = await db.execute(count_q)
            total = int(res.scalar() or 0)

            q = text(f"SELECT access_group, COUNT(1) as cnt FROM {meta_table('schemas')} GROUP BY access_group ORDER BY access_group LIMIT :limit OFFSET :offset")
            rows = (await db.execute(q, {"limit": int(limit), "offset": int(offset)})).fetchall()
        else:
            # Regular users only see their groups (intersection)
            if not u_groups:
                return {"items": [], "total": 0}
            # Regular users only see their groups (intersection). Use Postgres ANY operator.
            q_count = text(f"SELECT COUNT(DISTINCT access_group) FROM {meta_table('schemas')} WHERE LOWER(access_group) = ANY(:g)")
            res = await db.execute(q_count, {"g": [g.lower() for g in u_groups]})
            total = int(res.scalar() or 0)

            q = text(f"SELECT access_group, COUNT(1) as cnt FROM {meta_table('schemas')} WHERE LOWER(access_group) = ANY(:g) GROUP BY access_group ORDER BY access_group LIMIT :limit OFFSET :offset")
            rows = (await db.execute(q, {"g": [g.lower() for g in u_groups], "limit": int(limit), "offset": int(offset)})).fetchall()

        items = [{"group": r.access_group, "count": int(r.cnt)} for r in rows]
        return {"items": items, "total": total}
    except Exception as e:
        logger.error(f"metadata groups error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    


@app.get("/api/schemas/{schema_id}/columns")
async def get_schema_columns(schema_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    try:
        res = await db.execute(text(f"SELECT column_name, data_type, required, validation FROM {meta_table('table_columns')} WHERE schema_id = :id ORDER BY column_name"), {"id": schema_id})
        rows = res.fetchall()
        return [{"column_name": r.column_name, "data_type": r.data_type, "required": r.required, "validation": r.validation} for r in rows]
    except Exception as e:
        logger.error(f"Schema columns error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/schemas/{schema_id}/versions")
async def get_schema_versions(schema_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    try:
        # Permission: user must belong to group or admin
        res = await db.execute(text(f"SELECT access_group FROM {meta_table('schemas')} WHERE id = :id"), {"id": schema_id})
        sch = res.fetchone()
        if not sch:
            raise HTTPException(status_code=404, detail='Schema not found')
        u_groups = user.get('groups', [])
        u_groups_l = set([str(g).strip().lower() for g in u_groups if g])
        if not any(str(g).upper() == 'ADMIN' for g in u_groups) and not (isinstance(sch.access_group, str) and sch.access_group.strip().lower() in u_groups_l):
            raise HTTPException(status_code=403, detail='Unauthorized')

        q = text(f"SELECT id, version, status, physical_table_name, created_by, created_at FROM {meta_table('schema_versions')} WHERE schema_id = :sid ORDER BY version DESC")
        rows = (await db.execute(q, {"sid": schema_id})).fetchall()
        items = [{"id": r.id, "version": r.version, "status": r.status, "physical_table_name": r.physical_table_name, "created_by": r.created_by, "created_at": getattr(r, 'created_at', None)} for r in rows]
        return {"items": items}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_schema_versions error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/debug/table/{table_name}")
async def debug_table(table_name: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """
    Debugging endpoint: returns the physical table column definitions.
    Accessible only to Admins.
    """
    try:
        u_groups = user.get('groups', [])
        is_admin = any(str(g).upper() == 'ADMIN' for g in u_groups)
        if not is_admin:
            raise HTTPException(status_code=403, detail='Admin required')

        # Validate identifier (allow optional schema.table or table)
        if not re.match(r'^[a-zA-Z0-9_\.]+$', table_name):
            raise HTTPException(status_code=400, detail='Invalid table name')

        # Optionally allow schema-qualified names like 'schema.table'
        if '.' in table_name:
            schema, tbl = table_name.split('.', 1)
        else:
            schema, tbl = 'public', table_name

        q = text("SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_schema = :schema AND table_name = :t ORDER BY ordinal_position")
        res = await db.execute(q, {"schema": schema, "t": tbl})
        rows = res.fetchall()
        cols = [{"column_name": r.column_name, "data_type": r.data_type, "is_nullable": r.is_nullable, "column_default": r.column_default} for r in rows]
        return {"table": f"{schema}.{tbl}", "columns": cols}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"debug_table error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/debug/coerce-row")
async def debug_coerce_row(schema_id: int, payload: Dict[str, Any], db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Admin-only: take a sample row payload and return the coerced params and their Python types without inserting.
    Request JSON: { "schema_id": int, "row": { col: value }, "enforce_required": true|false }
    """
    # Admin check
    u_groups = user.get('groups', [])
    is_admin = any(str(g).upper() == 'ADMIN' for g in u_groups)
    if not is_admin:
        raise HTTPException(status_code=403, detail='Admin required')

    try:
        row = payload.get('row') if payload else None
        enforce = bool(payload.get('enforce_required', True)) if payload else True
        if not isinstance(row, dict):
            raise HTTPException(status_code=400, detail='row must be an object')

        # load columns metadata
        colres = await db.execute(text(f"SELECT column_name, data_type, required, validation FROM {meta_table('table_columns')} WHERE schema_id = :id"), {"id": schema_id})
        cols = {r.column_name: {"data_type": r.data_type, "required": r.required, "validation": r.validation} for r in colres.fetchall()}
        if not cols:
            raise HTTPException(status_code=400, detail='No column metadata for schema')

        # Filter incoming to known columns
        incoming = {k: v for k, v in row.items() if k in cols}

        params, keys = _validate_and_coerce_row(incoming, cols, enforce_required=enforce)

        types = {k: type(v).__name__ for k, v in params.items()}
        # Return both coerced params (serialized where necessary) and types
        serializable = {}
        for k, v in params.items():
            if isinstance(v, (datetime.datetime, datetime.date)):
                serializable[k] = v.isoformat()
            else:
                try:
                    json.dumps(v)
                    serializable[k] = v
                except Exception:
                    serializable[k] = str(v)

        return {"params": serializable, "types": types, "keys": keys}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"debug_coerce_row error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
