"""Video to Frames Plugin

Operators:
  - convert_to_frames — samples video frames to images and saves a frames view

Wraps :meth:`fiftyone.core.collections.SampleCollection.to_frames`. Frames are
sampled once (``sample_frames=True``), then the view is saved with
``sample_frames=False`` so loading it later doesn't re-check every image in
storage. Frames views are linked to the source videos: label edits made on
frames are synced back to the video dataset.
"""

import fiftyone.operators as foo
import fiftyone.operators.types as types

RATE_CHOICES = {
    "native": "All frames",
    "fps": "Fixed FPS",
    "max_fps": "Max FPS",
}

#: Max height choices; frames keep their aspect ratio
SIZE_CHOICES = {
    "original": "Original",
    "2160": "2160p (4K)",
    "1440": "1440p",
    "1080": "1080p",
    "720": "720p",
    "480": "480p",
}


class ConvertToFrames(foo.Operator):
    @property
    def config(self):
        return foo.OperatorConfig(
            name="convert_to_frames",
            label="Convert video to frames",
            description="Sample video frames to images and save a frames view",
            icon="burst_mode",
            dynamic=True,
            allow_immediate_execution=True,
            allow_delegated_execution=True,
            default_choice_to_delegated=True,
        )

    def resolve_placement(self, ctx):
        if not _is_video(ctx):
            return None

        return types.Placement(
            types.Places.SAMPLES_GRID_SECONDARY_ACTIONS,
            types.Button(
                label="Convert video to frames",
                icon="burst_mode",
                prompt=True,
            ),
        )

    def resolve_input(self, ctx):
        inputs = types.Object()

        if not _is_video(ctx):
            inputs.view(
                "error",
                types.Error(label="This operator requires a video dataset"),
            )
            return types.Property(inputs)

        inputs.view_target(ctx)

        rate_group = types.RadioGroup()
        for value, label in RATE_CHOICES.items():
            rate_group.add_choice(value, label=label)

        inputs.enum(
            "rate",
            rate_group.values(),
            default="native",
            label="Frame rate",
            description=(
                "All frames keeps every frame. Fixed FPS samples exactly N "
                "frames per second. Max FPS only downsamples videos above N"
            ),
            view=rate_group,
        )

        rate = ctx.params.get("rate", "native")
        if rate != "native":
            inputs.float(
                "fps",
                default=1.0,
                required=True,
                min=0.01,
                label="Frames per second",
            )

        size_dropdown = types.DropdownView()
        for value, label in SIZE_CHOICES.items():
            size_dropdown.add_choice(value, label=label)

        inputs.enum(
            "max_height",
            size_dropdown.values(),
            default="original",
            label="Max frame height",
            description="Larger frames are resized, keeping the aspect ratio",
            view=size_dropdown,
        )

        inputs.str(
            "output_dir",
            label="Output directory",
            description=(
                "Where to write the frame images, e.g. "
                "gs://my-bucket/frames. By default, a folder next to each "
                "video with the video's name"
            ),
        )

        inputs.bool(
            "force_sample",
            default=False,
            label="Re-sample existing frames",
            description=(
                "Frames that were already sampled are reused. Enable this to "
                "re-sample them, e.g. at a different size"
            ),
        )

        inputs.str(
            "view_name",
            default=_default_view_name(ctx.params),
            required=True,
            label="Saved view name",
            description="The frames view is saved on this dataset under this name",
        )

        if ctx.dataset.has_saved_view(ctx.params.get("view_name") or ""):
            inputs.view(
                "overwrite_warning",
                types.Warning(
                    label="A saved view with this name exists and will be overwritten"
                ),
            )

        return types.Property(
            inputs, view=types.View(label="Convert video to frames")
        )

    def execute(self, ctx):
        target = ctx.target_view()
        rate = ctx.params.get("rate", "native")
        fps = ctx.params.get("fps") if rate == "fps" else None
        max_fps = ctx.params.get("fps") if rate == "max_fps" else None
        max_height = ctx.params.get("max_height", "original")
        max_size = None if max_height == "original" else (-1, int(max_height))
        view_name = ctx.params["view_name"]

        # Sample the frame images and store their paths on the video frames.
        # Fail loudly: with skip_failures=True, FiftyOne still records the
        # planned frame paths, so a failed video yields a view of broken images
        target.to_frames(
            sample_frames=True,
            fps=fps,
            max_fps=max_fps,
            max_size=max_size,
            output_dir=ctx.params.get("output_dir") or None,
            force_sample=ctx.params.get("force_sample", False),
            skip_failures=False,
        )

        # Frames now have filepaths, so the saved view doesn't need to sample
        frames = target.to_frames(fps=fps, max_fps=max_fps)
        ctx.dataset.save_view(view_name, frames, overwrite=True)

        if not ctx.delegated:
            ctx.ops.set_view(name=view_name)

        return {"view_name": view_name, "num_frames": len(frames)}

    def resolve_output(self, ctx):
        outputs = types.Object()
        outputs.str("view_name", label="Saved view")
        outputs.int("num_frames", label="Frames")
        return types.Property(
            outputs, view=types.View(label="Frames view created")
        )


def _is_video(ctx):
    return ctx.dataset is not None and ctx.view.media_type == "video"


def _default_view_name(params):
    rate = params.get("rate", "native")
    fps = params.get("fps") or 1.0
    name = "frames"
    if rate == "fps":
        name += f"-{fps:g}fps"
    elif rate == "max_fps":
        name += f"-max-{fps:g}fps"

    max_height = params.get("max_height", "original")
    if max_height != "original":
        name += f"-{max_height}p"

    return name


def register(p):
    p.register(ConvertToFrames)
