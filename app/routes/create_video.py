#/routes/create_video.py
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip, CompositeVideoClip, concatenate, ColorClip
from moviepy.video.fx.fadein import fadein
from moviepy.video.fx.fadeout import fadeout
import os
import tempfile
import psycopg2
from flask import current_app, Blueprint, jsonify, session, url_for, request

video_creation_blueprint = Blueprint('video', __name__)

def get_db_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"])

def get_user_id(username):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
    user_id = cur.fetchone()[0]
    cur.close()
    return user_id

def create_temp_preview_filename(user_id):
    return f"temp_preview_{user_id}.mp4"

def slide_transition(clip1, clip2, direction):
    """
    Slides clip2 over clip1 from the specified direction.
    """
    clip1 = clip1.set_duration(clip2.duration + 1)
    if direction == 'right':
        clip2 = clip2.set_position(lambda t: (max(0, t-1) * clip2.w, 0))
    elif direction == 'left':
        clip2 = clip2.set_position(lambda t: (max(0, 1-t) * -clip2.w, 0))
    final_clip = CompositeVideoClip([clip1, clip2.set_start(1)])
    return final_clip.set_duration(clip1.duration)

def wipe_transition(clip1, clip2, direction='horizontal'):
    """
    Wipe effect from clip1 to clip2. This example assumes a horizontal wipe.
    """
    w, h = clip1.size
    mask = ColorClip(clip1.size, color=1, is_mask=True)
    
    if direction == 'horizontal':
        mask = mask.set_position(lambda t: (-w + t*(w/clip2.duration), 0))
    else:
        mask = mask.set_position(lambda t: (0, -h + t*(h/clip2.duration)))
    
    clip2_masked = clip2.set_mask(mask)
    final_clip = CompositeVideoClip([clip1, clip2_masked.set_start(1)], size=clip1.size)
    return final_clip.set_duration(clip1.duration + clip2.duration - 1)

def apply_transition(clip1, clip2, transition_type):
    if transition_type == 'fade':
        clip1 = clip1.fx(fadeout, 1)
        clip2 = clip2.fx(fadein, 1)
        return concatenate_videoclips([clip1, clip2], padding=-1, method="compose")

    elif transition_type == 'crossfade':
        return concatenate_videoclips([clip1, clip2], padding=-1, method="compose")

    elif transition_type == 'slideright':
        final_clip = slide_transition(clip1, clip2, 'right')
        return final_clip

    elif transition_type == 'wipe':
        final_clip = wipe_transition(clip1, clip2, direction='horizontal')
        return final_clip

    elif transition_type == 'blackfade':
        black_clip = ColorClip(clip1.size, color=(0, 0, 0)).set_duration(1)
        clip1 = clip1.fx(fadeout, 1)
        clip2 = clip2.fx(fadein, 1)
        return concatenate_videoclips([clip1, black_clip, clip2], padding=-1, method="compose")

    elif transition_type == 'slideleft':
        final_clip = slide_transition(clip1, clip2, 'left')
        return final_clip

    else:
        # Default to no transition
        return concatenate_videoclips([clip1, clip2])

def create_video_with_transitions_and_audio(user_id, transitionsArray, videoComposition, final=False):
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    
    #cur.execute("SELECT image_blob FROM images WHERE user_id = %s ORDER BY uploaded_at", (user_id,))
    
    
    # Check if the length of transitionsArray matches expectations
    if len(transitionsArray) != len(videoComposition) - 1:
        # Print lengths on the console
        print(f"Length of transitionsArray: {len(transitionsArray)}")
        print(f"Number of images: {len(videoComposition)}")
        cur.close()
        # Handle the error appropriately. Here's an example of raising an exception:
        raise ValueError("The length of transitionsArray must be exactly one less than the number of images.")
    clips = []
    # Assuming transitionsArray is aligned with images_data, but has one less element
    # because transitions are between images.
    for i, selected_img_src in enumerate(videoComposition):
        cur = conn.cursor()

        # Assuming image_ref is an image ID for simplicity
        # Adjust the query if image_ref refers to something else (e.g., filename)
        cur.execute("SELECT image_blob FROM images WHERE user_id = %s AND id = %s", (user_id, image_ref))

        image_blob = cur.fetchone()
        with tempfile.NamedTemporaryFile(delete=True, suffix='.jpg') as temp_image:
            temp_image.write(image_blob[0])  # Adjusted for blob unpacking
            temp_image.flush()
            clip = ImageClip(temp_image.name).set_duration(2)
            
            
            if i > 0:  # For subsequent images, apply transition from the previous image
                transition_type = transitionsArray[i-1]  # Aligning transition index with image
                clip = apply_transition(clips[-1], clip, transition_type)
                clips[-1] = clip
            else:
                clips.append(clip)
    
    final_clip = concatenate_videoclips(clips, method="compose")
    
    cur.execute("SELECT audio_blob FROM audio_library WHERE user_id = %s", (user_id,))
    audio_blob = cur.fetchone()
    if audio_blob:
        with tempfile.NamedTemporaryFile(delete=True, suffix='.mp3') as temp_audio:
            temp_audio.write(audio_blob[0])
            temp_audio.flush()
            audio_clip = AudioFileClip(temp_audio.name)
            final_clip = final_clip.set_audio(audio_clip)

    output_filename = "temp_preview.mp4" if not final else "final_video.mp4"
    output_path = os.path.join(current_app.config['UPLOAD_FOLDER'], output_filename)
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
    cur.close()
    
    if final:
        temp_preview_path = os.path.join(current_app.config['UPLOAD_FOLDER'], "temp_preview.mp4")
        if os.path.exists(temp_preview_path):
            os.remove(temp_preview_path)

    return output_path

@video_creation_blueprint.route('/preview', methods=['POST'])
def preview_video():
    if 'username' not in session:
        return jsonify({"status": "error", "message": "You must be logged in to preview videos."}), 403
    username = session['username']
    user_id = get_user_id(username)
    data = request.get_json()
    transitionsArray = data.get('transitions', [])
    videoComposition = data.get('composition', [])
    video_path = create_video_with_transitions_and_audio(user_id, transitionsArray, videoComposition, final=False)
    video_url = url_for('static', filename=os.path.relpath(video_path, start=current_app.static_folder), _external=True)
    return jsonify({"status": "success", "message": "Preview ready.", "video_url": video_url})

@video_creation_blueprint.route('/create_final', methods=['POST'])
def create_final_video():
    if 'username' not in session:
        return jsonify({"status": "error", "message": "You must be logged in to create videos."}), 403
    username = session['username']
    user_id = get_user_id(username)
    data = request.get_json()
    transitionsArray = data.get('transitions', [])
    videoComposition = data.get('composition', [])
    video_path = create_video_with_transitions_and_audio(user_id, transitionsArray, videoComposition, final=False)
    video_url = url_for('static', filename=os.path.relpath(video_path, start=current_app.static_folder), _external=True)
    return jsonify({"status": "success", "message": "Final video successfully created.", "video_url": video_url})
