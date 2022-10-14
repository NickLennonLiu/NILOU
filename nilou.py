from time import sleep
import os
from secret import api, proxies
import requests
import json
import heapq

uri = "https://danbooru.donmai.us"

auth = {
	"$login": api
}

use_fields = {"source", "tag_string", "fav_count", "tag_count_general", "tag_count_artist", "tag_count_character",
			  "file_url", "preview_file_url"}

def get_pages(tags, page=1, limit=20):
	payload = {
		**auth,
		"tags": tags,
		"format": "json",
		"page": page,
		"limit": limit
	}
	res = requests.get(uri + "/posts.json", proxies=proxies, params=payload)
	if res.status_code != 200:
		print(f"Failed to get {tags} on page {page}")
		return
	ls = json.loads(res.content)
	return ls

def get_search_result(preview_dir, meta_dir, tags, num, limit=20):
	for i in range(int(num/limit)):
		sleep(1)
		page_result = []
		page = get_pages(tags, i+1)
		for image in page:
			try:
				page_result.append({
					key:image[key] for key in use_fields
				})
			except KeyError as e:
				continue
		print(f"Fetched page {i+1}")
		get_preview(preview_dir, meta_dir, page_result)

def get_preview(preview_dir, meta_dir, search_result):
	assert os.path.exists(preview_dir), "preview_dir not exists!"
	assert os.path.exists(meta_dir), "meta_dir not exists!"
	print(f"Downloading {len(search_result)} images")
	for image in search_result:
		filename = image["preview_file_url"].split('/')[-1].split('.')[0]
		r = requests.get(image["preview_file_url"])
		with open(os.path.join(preview_dir, filename+".jpg"), 'wb') as f:
			f.write(r.content)
		with open(os.path.join(meta_dir, filename+".json"), 'w') as f:
			json.dump(image, f)

def get_topk_tags(meta_dir, topk, output_file=None):
	all_tags = {}
	for filename in os.listdir(meta_dir):
		with open(os.path.join(meta_dir, filename), 'r') as f:
			tags = json.load(f)["tag_string"].split(' ')
			for tag in tags:
				if tag in all_tags:
					all_tags[tag] += 1
				else:
					all_tags[tag] = 1
	k_tags = heapq.nlargest(topk, all_tags, key=all_tags.__getitem__)
	print(k_tags)
	if output_file:
		with open(output_file, "w") as f:
			f.write(', '.join(k_tags))

def remove_undesired_pics(preview_dir, meta_dir):
	hash_list = []
	for filename in os.listdir(preview_dir):
		image_hash = os.path.splitext(filename)[0]
		hash_list.append(image_hash)
	for filename in os.listdir(meta_dir):
		image_hash = os.path.splitext(filename)[0]
		if image_hash not in hash_list:
			os.remove(os.path.join(meta_dir, image_hash+".json"))

def get_original_images(meta_dir, image_dir):
	for filename in os.listdir(meta_dir):
		image_hash = os.path.splitext(filename)[0]
		with open(os.path.join(meta_dir, filename), 'r') as f:
			meta = json.load(f)
		r = requests.get(meta["file_url"])
		with open(os.path.join(image_dir, image_hash + ".jpg"), 'wb') as f:
			f.write(r.content)

def make_dirs():
	if not os.path.exists("./preview"):
		os.mkdir("./preview")
	if not os.path.exists("./meta"):
		os.mkdir("./meta")
	if not os.path.exists("./image"):
		os.mkdir("./image")

if __name__ == "__main__":
	tags = input("input your tags: ")
	num = input("number of pictures you want(100 by default): ")
	if num == "":
		num = 100
	else:
		num = int(num)

	make_dirs()

	#get_search_result("./preview", "./meta", "nilou_(genshin_impact)", 100)
	get_search_result("./preview", "./meta", tags, num)
	input("now delete the pictures you don't want, after that, press any key to continue: ")
	remove_undesired_pics("./preview", "./meta")
	get_topk_tags("./meta", 20, "./top20_tags.txt")
	get_original_images("./meta", "./image")

