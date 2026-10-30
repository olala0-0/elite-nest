def migrate(cr, version):
    cr.execute("UPDATE rent_contract SET state = 'terminate' WHERE state = 'close'")
