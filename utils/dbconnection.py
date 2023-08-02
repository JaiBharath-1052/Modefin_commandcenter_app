import settings


async def fetchSingle(query):
    async with settings.SessionLocal as SessionLocal:
        async with SessionLocal.begin_nested():
            result_obj_query = query
            result_obj = await SessionLocal.execute(result_obj_query)
            result_obj = result_obj.scalars().first()
    return result_obj
                


async def fetchMany(query):
    async with settings.SessionLocal as SessionLocal:
        async with SessionLocal.begin_nested():
            result_obj_list_query = query
            result_obj_list = await SessionLocal.execute(result_obj_list_query)
            result_obj_list = result_obj_list.scalars().all()
    return result_obj_list
    

async def updateObject(object):
    async with settings.SessionLocal as SessionLocal:
        async with SessionLocal.begin_nested():
            SessionLocal.add(object)
        await SessionLocal.commit()
    return object
            
        
            