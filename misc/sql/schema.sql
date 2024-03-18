CREATE table IF NOT EXISTS sessions (
  id varchar,
  session JSON,
  created bigint,
  expires bigint,
  paymentid varchar,
  gateid varchar,
  spaceid varchar
)

CREATE table IF NOT EXISTS vdp (
  id varchar,
  version varchar,
  revision bigint,
  tpe varchar,
  data JSON,
  deleted bool,
  my bool,
  readonly bool,
  expiry int,
  ttl int
)
