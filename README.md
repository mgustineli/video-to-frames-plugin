# Video to Frames Plugin for FiftyOne

A [FiftyOne](https://github.com/voxel51/fiftyone) plugin that converts a video dataset into a **frames view**: one image sample per video frame, with all frame-level labels, at the frame rate and size you choose.

The frames view lives on the same dataset as your videos. Label edits made on frames are synced back to the videos, so you don't need a separate image dataset.

## Installation

```shell
fiftyone plugins download https://github.com/mgustineli/video-to-frames-plugin
```

### FiftyOne Enterprise

Plugins are installed on the deployment by an admin:

1. Download the repo as a zip: [video-to-frames-plugin-main.zip](https://github.com/mgustineli/video-to-frames-plugin/archive/refs/heads/main.zip)
2. In the App, go to **Settings → Plugins → Install plugin** and upload the zip

Or with the SDK, as an admin:

```python
import fiftyone.management as fom

fom.upload_plugin("video-to-frames-plugin-main.zip", overwrite=True)
```

Background (delegated) runs need a delegated operator orchestrator on the deployment. Without one, choose **Execute now** when running the operator.

## Usage

1. Open a **video dataset** in the App
2. Click **Convert video to frames** in the samples grid actions (or find it in the operator browser)
3. Pick the options and run:

| Option | Description |
|--------|-------------|
| Target | The whole dataset, the current view, or the selected samples |
| Frame rate | **All frames**, **Fixed FPS** (exactly N frames per second) or **Max FPS** (only downsample videos above N) |
| Max frame height | Resize larger frames, keeping the aspect ratio (e.g. 4K → 1080p) |
| Output directory | Where to write the frame images, e.g. `gs://my-bucket/frames`. By default, a folder next to each video |
| Re-sample existing frames | Frames that were already sampled are reused; enable this to re-sample them (e.g. at a new size) |
| Saved view name | The frames view is saved on the dataset under this name |

When run immediately, the App opens the frames view when it's done. When run in the background (delegated), open the saved view from the view selector once the run finishes.

Frames are sampled once. The saved view only references the sampled images, so loading it later is fast.

## Notes

- Sampling decodes every video with ffmpeg, so long or high-resolution videos take a while. Background (delegated) execution is the default.
- The output location must be writable by the deployment (or by your SDK credentials when running locally). With cloud media, frames are written back to the same bucket by default.
- If a video can't be sampled, the operation fails with an error instead of creating a view with missing images.
- Frames that already exist are not resized. To change the size of frames you already sampled, enable **Re-sample existing frames**.

## SDK equivalent

The operator wraps [`to_frames()`](https://docs.voxel51.com/api/fiftyone.core.collections.html#fiftyone.core.collections.SampleCollection.to_frames):

```python
import fiftyone as fo

dataset = fo.load_dataset("my-videos")

# Sample frames at 1 fps, at most 1080p tall
dataset.to_frames(sample_frames=True, fps=1, max_size=(-1, 1080))

# Save a frames view that uses the sampled images
frames = dataset.to_frames(fps=1)
dataset.save_view("frames-1fps-1080p", frames)
```

## License

MIT
