from flask import Blueprint, render_template

posts_bp = Blueprint("posts_bp", __name__, template_folder="../templates")

@posts_bp.route("/feed")
def feed():
    # Dummy Stories
    stories = [
        {"img": "https://i.pravatar.cc/120?img=15", "user_id": "Rohit"},
        {"img": "https://i.pravatar.cc/120?img=25", "user_id": "Aisha"},
        {"img": "https://i.pravatar.cc/120?img=35", "user_id": "Dev"},
        {"img": "https://i.pravatar.cc/120?img=45", "user_id": "Simran"},
        {"img": "https://i.pravatar.cc/120?img=55", "user_id": "Kabir"},
        {"img": "https://i.pravatar.cc/120?img=65", "user_id": "Nikki"},
    ]

    # Instagram Style Posts Feed
    posts = [
        {
            "user_id": "Rohit",
            "user_img": "https://i.pravatar.cc/100?img=12",
            "image": "https://picsum.photos/600/800?random=10",
            "caption": "Weekend mood 🔥"
        },
        {
            "user_id": "Aisha",
            "user_img": "https://i.pravatar.cc/100?img=18",
            "image": "https://picsum.photos/600/800?random=14",
            "caption": "New day, new energy ✨"
        },
        {
            "user_id": "Simran",
            "user_img": "https://i.pravatar.cc/100?img=22",
            "image": "https://picsum.photos/600/800?random=19",
            "caption": "Sunset feels 💛"
        },
        {
            "user_id": "Kabir",
            "user_img": "https://i.pravatar.cc/100?img=29",
            "image": "https://picsum.photos/600/800?random=28",
            "caption": "Gym sessions 🔥"
        }
    ]

    return render_template("feed.html", stories=stories, posts=posts)
