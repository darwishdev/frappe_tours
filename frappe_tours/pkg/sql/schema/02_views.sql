create OR REPLACE view    web_page_view as
with translations AS (
    SELECT
        parent_id,
        locale,
        JSON_ARRAYAGG(
            JSON_OBJECT(
                'field', translated_field,
                'translated_value', translated_value
            )
        ) AS field_list
    FROM `tabWeb Translations`
    WHERE parent_type = 'Web Page Block'
    GROUP BY parent_id, locale
) ,translation_map as (
  SELECT
    parent_id,
    -- Step 2: Map the locales as keys to their respective arrays
    JSON_OBJECTAGG(locale, field_list) AS translations
FROM translations
GROUP BY parent_id ) , blocks as (
  select  wpb.parent,
    JSON_ARRAYAGG(
       JSON_OBJECT(
        'web_template', wpb.web_template,
        'web_template_values', wpb.web_template_values,
        'hide_block', wpb.hide_block,
        'idx', wpb.idx,
        'translations' ,t.translations
      )
    ) blocks
  from `tabWeb Page Block` wpb
LEFT JOIN translation_map t ON wpb.name = t.parent_id
  where wpb.parenttype = 'Web Page'
  GROUP BY wpb.parent
 ) , meta_tags as (
  SELECT m.parent , JSON_ARRAYAGG(
        JSON_OBJECT(
            'key', m.`key`,
            'value', m.`value`
        )
    ) meta_tags FROM `tabWebsite Meta Tag` m
      WHERE  m.parenttype = 'Web Page'
  GROUP BY m.parent
 )
select
wp.name,
wp.title,
wp.route,
wp.content_type,
wp.meta_title,
wp.meta_description,
wp.meta_image,
wp.header,
wp.breadcrumbs,
m.meta_tags,
b.blocks
from `tabWeb Page` wp
LEFT JOIN meta_tags m on wp.name = m.parent
LEFT JOIN blocks b on  wp.name = b.parent;
