import os
from dotenv import load_dotenv
from graph_store import GraphStore, Neo4jConfig

def main():
    load_dotenv()
    gs = GraphStore(Neo4jConfig(
        uri=os.environ["NEO4J_URI"],
        user=os.environ["NEO4J_USER"],
        password=os.environ["NEO4J_PASSWORD"],
    ))
    gs.ensure_constraints()

    user_id = os.environ["USER_ID"]
    title = input("Task title: ").strip()
    place = input("Place hint (optional): ").strip() or None
    task_id = gs.add_task(user_id, title, place_hint=place)
    print("Created task:", task_id)

if __name__ == "__main__":
    main()
