# Page navigation cards

Current design:470×264 native Kodi navigation cards matching the ordinary title-art footprint and spacing. Preserve the photographed style: font20_title header with BlackLan white and only turn cyan; regular font27 Previous/Next label; font20_title Browse more titles footer; orbit-arrow lantern on the right. Labels are native XML controls, not baked into the PNGs. Native focus border fits470×264. Previous keeps text left and lantern right; Next mirrors the columns, with lantern left and text/chevron right. Other artwork geometry is unchanged.

The two transparent lantern variants were made with the built-in image-editing tool from the existing BlackLanturn lantern and retained here. Do not regenerate them during packaging. Run `python3 branding/page-cards/render.py` from the source root to reproduce the transparent512px exports at addon/resources/media/page-previous.png and page-next.png. No external font files or font build inputs are required.

The controller normalizes both directions to local navigation art and renders them as paging-kind. Next retains the provider route; Previous uses existing history and exact selection restoration. The prior square-card recipe is archived with local task evidence. Native rendering was requested by the user to preserve the skin font exactly.
