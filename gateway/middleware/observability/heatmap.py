from fastapi import Request

async def record_table_access(request: Request, table: str):
    redis = request.app.state.redis
    await redis.zincrby("siqg:heatmap:tables", 1, table)

async def get_heatmap(redis) -> list:
    entries = await redis.zrevrange("siqg:heatmap:tables", 0, -1, withscores=True)
    return [{"table": name, "query_count": int(score)} for name, score in entries]
