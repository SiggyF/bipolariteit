<?xml version='1.0' encoding='utf-8'?>
<qgis version="3.44.11-Solothurn" styleCategories="AllStyleCategories"><flags>
        <Identifiable>1</Identifiable>
        <Removable>1</Removable>
        <Searchable>1</Searchable>
        <Private>0</Private>
      </flags>
      <customproperties>
        <Option type="Map">
          <Option name="embeddedWidgets/count" type="int" value="0" />
          <Option name="variableNames" />
          <Option name="variableValues" />
        </Option>
      </customproperties>
      <geometryOptions geometryPrecision="0" removeDuplicateNodes="0">
        <activeChecks />
        <checkConfiguration type="Map">
          <Option name="QgsGeometryGapCheck" type="Map">
            <Option name="allowedGapsBuffer" type="double" value="0" />
            <Option name="allowedGapsEnabled" type="bool" value="false" />
            <Option name="allowedGapsLayer" type="QString" value="" />
          </Option>
        </checkConfiguration>
      </geometryOptions>
      <renderer-v2 enableorderby="0" forceraster="0" referencescale="-1" symbollevels="0" type="singleSymbol">
        <symbols>
          <symbol alpha="0.704" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="0" type="fill">
            <data_defined_properties>
              <Option type="Map">
                <Option name="name" type="QString" value="" />
                <Option name="properties" />
                <Option name="type" type="QString" value="collection" />
              </Option>
            </data_defined_properties>
            <layer class="SimpleFill" enabled="1" id="{c875adef-9e35-4a90-a6bf-308e9a05eae3}" locked="0" pass="0">
              <Option type="Map">
                <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                <Option name="color" type="QString" value="0,0,255,255,rgb:0,0,1,1" />
                <Option name="joinstyle" type="QString" value="bevel" />
                <Option name="offset" type="QString" value="0,0" />
                <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                <Option name="offset_unit" type="QString" value="MM" />
                <Option name="outline_color" type="QString" value="0,0,0,255,hsv:0.28055554628372192,0.50980395078659058,0,1" />
                <Option name="outline_style" type="QString" value="solid" />
                <Option name="outline_width" type="QString" value="1.5" />
                <Option name="outline_width_unit" type="QString" value="MM" />
                <Option name="style" type="QString" value="no" />
              </Option>
              <data_defined_properties>
                <Option type="Map">
                  <Option name="name" type="QString" value="" />
                  <Option name="properties" type="Map">
                    <Option name="outlineColor" type="Map">
                      <Option name="active" type="bool" value="true" />
                      <Option name="expression" type="QString" value="CASE &#10;  WHEN &quot;level&quot; = 0 THEN '#22304e'   -- Niveau 0: Diepe Staten-Generaal Navy (hoofdhulls)&#10;  WHEN &quot;level&quot; = 1 THEN '#33456e'   -- Niveau 1: Bipolariteit Accent Navy&#10;  WHEN &quot;level&quot; = 2 THEN '#4d5d7d'   -- Niveau 2: Gedempt leisteenblauw&#10;  WHEN &quot;level&quot; = 3 THEN '#6f7e99'   -- Niveau 3: Zacht middengrijsblauw&#10;  WHEN &quot;level&quot; = 4 THEN '#98a4ba'   -- Niveau 4: Fijne inktwaas&#10;  ELSE '#bcc5d4'&#10;END" />
                      <Option name="type" type="int" value="3" />
                    </Option>
                    <Option name="outlineWidth" type="Map">
                      <Option name="active" type="bool" value="true" />
                      <Option name="expression" type="QString" value="CASE &#10;  WHEN &quot;level&quot; = 0 THEN 1.10   -- Niveau 0: Krachtige hoofdomtrek (~3.2 pt)&#10;  WHEN &quot;level&quot; = 1 THEN 0.75   -- Niveau 1: Grote thema's (~2.2 pt)&#10;  WHEN &quot;level&quot; = 2 THEN 0.50   -- Niveau 2: Hoofdonderwerpen (~1.4 pt)&#10;  WHEN &quot;level&quot; = 3 THEN 0.32   -- Niveau 3: Sub-debatten (~0.9 pt)&#10;  WHEN &quot;level&quot; = 4 THEN 0.18   -- Niveau 4: Ragfijne micro-debatten (~0.5 pt)&#10;  ELSE 0.12&#10;END" />
                      <Option name="type" type="int" value="3" />
                    </Option>
                  </Option>
                  <Option name="type" type="QString" value="collection" />
                </Option>
              </data_defined_properties>
            </layer>
          </symbol>
        </symbols>
        <rotation />
        <sizescale />
        <data-defined-properties>
          <Option type="Map">
            <Option name="name" type="QString" value="" />
            <Option name="properties" />
            <Option name="type" type="QString" value="collection" />
          </Option>
        </data-defined-properties>
      </renderer-v2>
      <selection mode="Default">
        <selectionColor invalid="1" />
        <selectionSymbol>
          <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="" type="fill">
            <data_defined_properties>
              <Option type="Map">
                <Option name="name" type="QString" value="" />
                <Option name="properties" />
                <Option name="type" type="QString" value="collection" />
              </Option>
            </data_defined_properties>
            <layer class="SimpleFill" enabled="1" id="{8fe219ae-3eef-4d87-a115-089a51cdcb5b}" locked="0" pass="0">
              <Option type="Map">
                <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                <Option name="color" type="QString" value="0,0,255,255,rgb:0,0,1,1" />
                <Option name="joinstyle" type="QString" value="bevel" />
                <Option name="offset" type="QString" value="0,0" />
                <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                <Option name="offset_unit" type="QString" value="MM" />
                <Option name="outline_color" type="QString" value="35,35,35,255,rgb:0.1372549,0.1372549,0.1372549,1" />
                <Option name="outline_style" type="QString" value="solid" />
                <Option name="outline_width" type="QString" value="0.26" />
                <Option name="outline_width_unit" type="QString" value="MM" />
                <Option name="style" type="QString" value="solid" />
              </Option>
              <data_defined_properties>
                <Option type="Map">
                  <Option name="name" type="QString" value="" />
                  <Option name="properties" />
                  <Option name="type" type="QString" value="collection" />
                </Option>
              </data_defined_properties>
            </layer>
          </symbol>
        </selectionSymbol>
      </selection>
      <labeling type="rule-based">
        <rules key="{4280c3cf-2078-435e-a74e-60e0dc3bacaf}">
          <rule description="Level 0 - Major Domains" filter="&quot;level&quot; = 0 AND &quot;name&quot; != 'Overig'" key="{37fcc803-13dd-4b42-9dd9-003ff1d3e387}" active="1">
            <settings calloutType="simple" priority="10" zIndex="10">
              <text-style allowHtml="0" blendMode="0" capitalization="1" fieldName="name" fontFamily="Libre Caslon Text" fontItalic="0" fontKerning="1" fontLetterSpacing="0" fontSize="16" fontSizeMapUnitScale="3x:0,0,0,0,0,0" fontSizeUnit="Point" fontStrikeout="0" fontUnderline="0" fontWeight="700" fontWordSpacing="0" forcedBold="0" forcedItalic="0" isExpression="0" legendString="Aa" multilineHeight="1" multilineHeightUnit="Percentage" namedStyle="Bold" previewBkgrdColor="255,255,255,255,rgb:1,1,1,1" stretchFactor="100" tabStopDistance="80" tabStopDistanceMapUnitScale="3x:0,0,0,0,0,0" tabStopDistanceUnit="Point" textColor="253,251,247,255,rgb:0.992,0.984,0.969,1" textOpacity="1" textOrientation="horizontal" useSubstitutions="0">
                <families />
                <text-buffer bufferBlendMode="0" bufferColor="242,239,231,255,rgb:0.9490196,0.9372549,0.9058824,1" bufferDraw="0" bufferJoinStyle="128" bufferNoFill="1" bufferOpacity="0.753" bufferSize="1" bufferSizeMapUnitScale="3x:0,0,0,0,0,0" bufferSizeUnits="MM" />
                <text-mask maskEnabled="0" maskJoinStyle="128" maskOpacity="1" maskSize="1.5" maskSize2="1.5" maskSizeMapUnitScale="3x:0,0,0,0,0,0" maskSizeUnits="MM" maskType="0" maskedSymbolLayers="" />
                <background shapeBlendMode="0" shapeBorderColor="58,77,112,255,rgb:0.227,0.302,0.439,1" shapeBorderWidth="0.35" shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeBorderWidthUnit="MM" shapeDraw="1" shapeFillColor="34,48,78,240,rgb:0.133,0.188,0.306,0.94" shapeJoinStyle="64" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeOffsetUnit="Point" shapeOffsetX="0" shapeOffsetY="0" shapeOpacity="0.94" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeRadiiUnit="MM" shapeRadiiX="1.0" shapeRadiiY="1.0" shapeRotation="0" shapeRotationType="0" shapeSVGFile="" shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeSizeType="0" shapeSizeUnit="MM" shapeSizeX="2.4" shapeSizeY="1.5" shapeType="0">
                  <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="markerSymbol" type="marker">
                    <data_defined_properties>
                      <Option type="Map">
                        <Option name="name" type="QString" value="" />
                        <Option name="properties" />
                        <Option name="type" type="QString" value="collection" />
                      </Option>
                    </data_defined_properties>
                    <layer class="SimpleMarker" enabled="1" id="" locked="0" pass="0">
                      <Option type="Map">
                        <Option name="angle" type="QString" value="0" />
                        <Option name="cap_style" type="QString" value="square" />
                        <Option name="color" type="QString" value="225,89,137,255,rgb:0.8823529,0.3490196,0.5372549,1" />
                        <Option name="horizontal_anchor_point" type="QString" value="1" />
                        <Option name="joinstyle" type="QString" value="bevel" />
                        <Option name="name" type="QString" value="circle" />
                        <Option name="offset" type="QString" value="0,0" />
                        <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                        <Option name="offset_unit" type="QString" value="MM" />
                        <Option name="outline_color" type="QString" value="35,35,35,255,rgb:0.1372549,0.1372549,0.1372549,1" />
                        <Option name="outline_style" type="QString" value="solid" />
                        <Option name="outline_width" type="QString" value="0" />
                        <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                        <Option name="outline_width_unit" type="QString" value="MM" />
                        <Option name="scale_method" type="QString" value="diameter" />
                        <Option name="size" type="QString" value="2" />
                        <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                        <Option name="size_unit" type="QString" value="MM" />
                        <Option name="vertical_anchor_point" type="QString" value="1" />
                      </Option>
                      <data_defined_properties>
                        <Option type="Map">
                          <Option name="name" type="QString" value="" />
                          <Option name="properties" />
                          <Option name="type" type="QString" value="collection" />
                        </Option>
                      </data_defined_properties>
                    </layer>
                  </symbol>
                  <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="fillSymbol" type="fill">
                    <data_defined_properties>
                      <Option type="Map">
                        <Option name="name" type="QString" value="" />
                        <Option name="properties" />
                        <Option name="type" type="QString" value="collection" />
                      </Option>
                    </data_defined_properties>
                    <layer class="SimpleFill" enabled="1" id="" locked="0" pass="0">
                      <Option type="Map">
                        <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                        <Option name="color" type="QString" value="34,48,78,240,rgb:0.133,0.188,0.306,0.94" />
                        <Option name="joinstyle" type="QString" value="bevel" />
                        <Option name="offset" type="QString" value="0,0" />
                        <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                        <Option name="offset_unit" type="QString" value="MM" />
                        <Option name="outline_color" type="QString" value="58,77,112,255,rgb:0.227,0.302,0.439,1" />
                        <Option name="outline_style" type="QString" value="solid" />
                        <Option name="outline_width" type="QString" value="0.35" />
                        <Option name="outline_width_unit" type="QString" value="MM" />
                        <Option name="style" type="QString" value="solid" />
                      </Option>
                      <data_defined_properties>
                        <Option type="Map">
                          <Option name="name" type="QString" value="" />
                          <Option name="properties" />
                          <Option name="type" type="QString" value="collection" />
                        </Option>
                      </data_defined_properties>
                    </layer>
                  </symbol>
                </background>
                <shadow shadowBlendMode="6" shadowColor="30,25,20,255,rgb:0.117,0.098,0.078,1" shadowDraw="1" shadowOffsetAngle="90" shadowOffsetDist="0.7" shadowOffsetGlobal="1" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowOffsetUnit="MM" shadowOpacity="0.25" shadowRadius="2.0" shadowRadiusAlphaOnly="0" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowRadiusUnit="MM" shadowScale="100" shadowUnder="1" />
                <dd_properties>
                  <Option type="Map">
                    <Option name="name" type="QString" value="" />
                    <Option name="properties" />
                    <Option name="type" type="QString" value="collection" />
                  </Option>
                </dd_properties>
                <substitutions />
              </text-style>
              <text-format addDirectionSymbol="0" autoWrapLength="0" decimals="3" formatNumbers="0" leftDirectionSymbol="&lt;" multilineAlign="3" placeDirectionSymbol="0" plussign="0" reverseDirectionSymbol="0" rightDirectionSymbol="&gt;" useMaxLineLengthForAutoWrap="1" wrapChar="" />
              <placement allowDegraded="0" centroidInside="0" centroidWhole="0" dist="1.2" distMapUnitScale="3x:0,0,0,0,0,0" distUnits="MM" fitInPolygonOnly="0" geometryGenerator="" geometryGeneratorEnabled="0" geometryGeneratorType="PointGeometry" labelOffsetMapUnitScale="3x:0,0,0,0,0,0" layerType="PolygonGeometry" lineAnchorClipping="0" lineAnchorPercent="0.5" lineAnchorTextPoint="FollowPlacement" lineAnchorType="0" maxCurvedCharAngleIn="25" maxCurvedCharAngleOut="-25" maximumDistance="0" maximumDistanceMapUnitScale="3x:0,0,0,0,0,0" maximumDistanceUnit="MM" multipartBehavior="LabelLargestPartOnly" offsetType="0" offsetUnits="MM" overlapHandling="PreventOverlap" overrunDistance="0" overrunDistanceMapUnitScale="3x:0,0,0,0,0,0" overrunDistanceUnit="MM" placement="0" placementFlags="10" polygonPlacementFlags="2" predefinedPositionOrder="TR,TL,BR,BL,R,L,TSR,BSR" preserveRotation="1" prioritization="PreferCloser" priority="10" quadOffset="4" repeatDistance="0" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0" repeatDistanceUnits="MM" rotationAngle="0" rotationUnit="AngleDegrees" xOffset="0" yOffset="0" obstacle="1" obstacleFactor="1" />
              <rendering drawLabels="1" fontLimitPixelSize="0" fontMaxPixelSize="10000" fontMinPixelSize="3" limitNumLabels="0" maxNumLabels="2000" mergeLines="1" minFeatureSize="0" obstacle="1" obstacleFactor="1" obstacleType="1" scaleMax="0" scaleMin="0" scaleVisibility="0" unplacedVisibility="0" upsidedownLabels="0" zIndex="10" displayAll="0" />
              <dd_properties>
                <Option type="Map">
                  <Option name="name" type="QString" value="" />
                  <Option name="properties" />
                  <Option name="type" type="QString" value="collection" />
                </Option>
              </dd_properties>
              <callout type="simple">
                <Option type="Map">
                  <Option name="anchorPoint" type="QString" value="pole_of_inaccessibility" />
                  <Option name="blendMode" type="int" value="0" />
                  <Option name="ddProperties" type="Map">
                    <Option name="name" type="QString" value="" />
                    <Option name="properties" />
                    <Option name="type" type="QString" value="collection" />
                  </Option>
                  <Option name="drawToAllParts" type="bool" value="false" />
                  <Option name="enabled" type="QString" value="1" />
                  <Option name="labelAnchorPoint" type="QString" value="point_on_exterior" />
                  <Option name="lineSymbol" type="QString" value="&lt;symbol alpha=&quot;1&quot; clip_to_extent=&quot;1&quot; force_rhr=&quot;0&quot; frame_rate=&quot;10&quot; is_animated=&quot;0&quot; name=&quot;symbol&quot; type=&quot;line&quot;&gt;&lt;data_defined_properties&gt;&lt;Option type=&quot;Map&quot;&gt;&lt;Option name=&quot;name&quot; type=&quot;QString&quot; value=&quot;&quot;/&gt;&lt;Option name=&quot;properties&quot;/&gt;&lt;Option name=&quot;type&quot; type=&quot;QString&quot; value=&quot;collection&quot;/&gt;&lt;/Option&gt;&lt;/data_defined_properties&gt;&lt;layer class=&quot;SimpleLine&quot; enabled=&quot;1&quot; id=&quot;{db2ade2b-1bed-44ce-b33a-83449199876e}&quot; locked=&quot;0&quot; pass=&quot;0&quot;&gt;&lt;Option type=&quot;Map&quot;&gt;&lt;Option name=&quot;align_dash_pattern&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;capstyle&quot; type=&quot;QString&quot; value=&quot;square&quot;/&gt;&lt;Option name=&quot;customdash&quot; type=&quot;QString&quot; value=&quot;5;2&quot;/&gt;&lt;Option name=&quot;customdash_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;customdash_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;dash_pattern_offset&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;dash_pattern_offset_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;dash_pattern_offset_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;draw_inside_polygon&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;joinstyle&quot; type=&quot;QString&quot; value=&quot;bevel&quot;/&gt;&lt;Option name=&quot;line_color&quot; type=&quot;QString&quot; value=&quot;60,60,60,255,rgb:0.2352941,0.2352941,0.2352941,1&quot;/&gt;&lt;Option name=&quot;line_style&quot; type=&quot;QString&quot; value=&quot;solid&quot;/&gt;&lt;Option name=&quot;line_width&quot; type=&quot;QString&quot; value=&quot;0.25&quot;/&gt;&lt;Option name=&quot;line_width_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;offset&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;offset_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;offset_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;ring_filter&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;trim_distance_end&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;trim_distance_end_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;trim_distance_end_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;trim_distance_start&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;trim_distance_start_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;trim_distance_start_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;tweak_dash_pattern_on_corners&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;use_custom_dash&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;width_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;/Option&gt;&lt;data_defined_properties&gt;&lt;Option type=&quot;Map&quot;&gt;&lt;Option name=&quot;name&quot; type=&quot;QString&quot; value=&quot;&quot;/&gt;&lt;Option name=&quot;properties&quot;/&gt;&lt;Option name=&quot;type&quot; type=&quot;QString&quot; value=&quot;collection&quot;/&gt;&lt;/Option&gt;&lt;/data_defined_properties&gt;&lt;/layer&gt;&lt;/symbol&gt;" />
                  <Option name="minLength" type="double" value="0" />
                  <Option name="minLengthMapUnitScale" type="QString" value="3x:0,0,0,0,0,0" />
                  <Option name="minLengthUnit" type="QString" value="MM" />
                  <Option name="offsetFromAnchor" type="double" value="0" />
                  <Option name="offsetFromAnchorMapUnitScale" type="QString" value="3x:0,0,0,0,0,0" />
                  <Option name="offsetFromAnchorUnit" type="QString" value="MM" />
                  <Option name="offsetFromLabel" type="double" value="0" />
                  <Option name="offsetFromLabelMapUnitScale" type="QString" value="3x:0,0,0,0,0,0" />
                  <Option name="offsetFromLabelUnit" type="QString" value="MM" />
                </Option>
              </callout>
            </settings>
          </rule>
          <rule description="Level 1 &amp; 2 - Topics" filter="&quot;level&quot; IN (1, 2) AND &quot;redundant_with_parent&quot; = false AND (&quot;name&quot; != &quot;parent_name&quot; OR &quot;parent_name&quot; IS NULL)" key="{9307154c-7ebd-44de-8478-bf6e42d9ec9d}" active="1">
            <settings calloutType="simple" priority="7" zIndex="7">
              <text-style allowHtml="0" blendMode="0" capitalization="0" fieldName="name" fontFamily="Libre Caslon Text" fontItalic="0" fontKerning="1" fontLetterSpacing="0" fontSize="10.5" fontSizeMapUnitScale="3x:0,0,0,0,0,0" fontSizeUnit="Point" fontStrikeout="0" fontUnderline="0" fontWeight="700" fontWordSpacing="0" forcedBold="0" forcedItalic="0" isExpression="0" legendString="Aa" multilineHeight="1" multilineHeightUnit="Percentage" namedStyle="Bold" previewBkgrdColor="255,255,255,255,rgb:1,1,1,1" stretchFactor="100" tabStopDistance="80" tabStopDistanceMapUnitScale="3x:0,0,0,0,0,0" tabStopDistanceUnit="Point" textColor="34,48,78,255,rgb:0.133,0.188,0.306,1" textOpacity="1" textOrientation="horizontal" useSubstitutions="0">
                <families />
                <text-buffer bufferBlendMode="0" bufferColor="242,239,231,255,rgb:0.9490196,0.9372549,0.9058824,1" bufferDraw="0" bufferJoinStyle="128" bufferNoFill="1" bufferOpacity="0.68799999999999994" bufferSize="0.69999999999999996" bufferSizeMapUnitScale="3x:0,0,0,0,0,0" bufferSizeUnits="MM" />
                <text-mask maskEnabled="0" maskJoinStyle="128" maskOpacity="1" maskSize="1.5" maskSize2="1.5" maskSizeMapUnitScale="3x:0,0,0,0,0,0" maskSizeUnits="MM" maskType="0" maskedSymbolLayers="" />
                <background shapeBlendMode="0" shapeBorderColor="69,88,125,200,rgb:0.271,0.345,0.490,0.78" shapeBorderWidth="0.24" shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeBorderWidthUnit="MM" shapeDraw="1" shapeFillColor="232,237,245,225,rgb:0.910,0.929,0.961,0.88" shapeJoinStyle="64" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeOffsetUnit="Point" shapeOffsetX="0" shapeOffsetY="0" shapeOpacity="0.88" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeRadiiUnit="MM" shapeRadiiX="0.8" shapeRadiiY="0.8" shapeRotation="0" shapeRotationType="0" shapeSVGFile="" shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeSizeType="0" shapeSizeUnit="MM" shapeSizeX="1.8" shapeSizeY="1.1" shapeType="0">
                  <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="markerSymbol" type="marker">
                    <data_defined_properties>
                      <Option type="Map">
                        <Option name="name" type="QString" value="" />
                        <Option name="properties" />
                        <Option name="type" type="QString" value="collection" />
                      </Option>
                    </data_defined_properties>
                    <layer class="SimpleMarker" enabled="1" id="" locked="0" pass="0">
                      <Option type="Map">
                        <Option name="angle" type="QString" value="0" />
                        <Option name="cap_style" type="QString" value="square" />
                        <Option name="color" type="QString" value="190,178,151,255,rgb:0.7450981,0.6980392,0.5921569,1" />
                        <Option name="horizontal_anchor_point" type="QString" value="1" />
                        <Option name="joinstyle" type="QString" value="bevel" />
                        <Option name="name" type="QString" value="circle" />
                        <Option name="offset" type="QString" value="0,0" />
                        <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                        <Option name="offset_unit" type="QString" value="MM" />
                        <Option name="outline_color" type="QString" value="35,35,35,255,rgb:0.1372549,0.1372549,0.1372549,1" />
                        <Option name="outline_style" type="QString" value="solid" />
                        <Option name="outline_width" type="QString" value="0" />
                        <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                        <Option name="outline_width_unit" type="QString" value="MM" />
                        <Option name="scale_method" type="QString" value="diameter" />
                        <Option name="size" type="QString" value="2" />
                        <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                        <Option name="size_unit" type="QString" value="MM" />
                        <Option name="vertical_anchor_point" type="QString" value="1" />
                      </Option>
                      <data_defined_properties>
                        <Option type="Map">
                          <Option name="name" type="QString" value="" />
                          <Option name="properties" />
                          <Option name="type" type="QString" value="collection" />
                        </Option>
                      </data_defined_properties>
                    </layer>
                  </symbol>
                  <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="fillSymbol" type="fill">
                    <data_defined_properties>
                      <Option type="Map">
                        <Option name="name" type="QString" value="" />
                        <Option name="properties" />
                        <Option name="type" type="QString" value="collection" />
                      </Option>
                    </data_defined_properties>
                    <layer class="SimpleFill" enabled="1" id="" locked="0" pass="0">
                      <Option type="Map">
                        <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                        <Option name="color" type="QString" value="232,237,245,225,rgb:0.910,0.929,0.961,0.88" />
                        <Option name="joinstyle" type="QString" value="bevel" />
                        <Option name="offset" type="QString" value="0,0" />
                        <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                        <Option name="offset_unit" type="QString" value="MM" />
                        <Option name="outline_color" type="QString" value="69,88,125,200,rgb:0.271,0.345,0.490,0.78" />
                        <Option name="outline_style" type="QString" value="solid" />
                        <Option name="outline_width" type="QString" value="0.24" />
                        <Option name="outline_width_unit" type="QString" value="MM" />
                        <Option name="style" type="QString" value="solid" />
                      </Option>
                      <data_defined_properties>
                        <Option type="Map">
                          <Option name="name" type="QString" value="" />
                          <Option name="properties" />
                          <Option name="type" type="QString" value="collection" />
                        </Option>
                      </data_defined_properties>
                    </layer>
                  </symbol>
                </background>
                <shadow shadowBlendMode="6" shadowColor="30,25,20,255,rgb:0.117,0.098,0.078,1" shadowDraw="1" shadowOffsetAngle="90" shadowOffsetDist="0.5" shadowOffsetGlobal="1" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowOffsetUnit="MM" shadowOpacity="0.16" shadowRadius="1.4" shadowRadiusAlphaOnly="0" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowRadiusUnit="MM" shadowScale="100" shadowUnder="1" />
                <dd_properties>
                  <Option type="Map">
                    <Option name="name" type="QString" value="" />
                    <Option name="properties" />
                    <Option name="type" type="QString" value="collection" />
                  </Option>
                </dd_properties>
                <substitutions />
              </text-style>
              <text-format addDirectionSymbol="0" autoWrapLength="0" decimals="3" formatNumbers="0" leftDirectionSymbol="&lt;" multilineAlign="3" placeDirectionSymbol="0" plussign="0" reverseDirectionSymbol="0" rightDirectionSymbol="&gt;" useMaxLineLengthForAutoWrap="1" wrapChar="" />
              <placement allowDegraded="0" centroidInside="0" centroidWhole="0" dist="1.2" distMapUnitScale="3x:0,0,0,0,0,0" distUnits="MM" fitInPolygonOnly="0" geometryGenerator="" geometryGeneratorEnabled="0" geometryGeneratorType="PointGeometry" labelOffsetMapUnitScale="3x:0,0,0,0,0,0" layerType="PolygonGeometry" lineAnchorClipping="0" lineAnchorPercent="0.5" lineAnchorTextPoint="FollowPlacement" lineAnchorType="0" maxCurvedCharAngleIn="25" maxCurvedCharAngleOut="-25" maximumDistance="0" maximumDistanceMapUnitScale="3x:0,0,0,0,0,0" maximumDistanceUnit="MM" multipartBehavior="LabelLargestPartOnly" offsetType="0" offsetUnits="MM" overlapHandling="PreventOverlap" overrunDistance="0" overrunDistanceMapUnitScale="3x:0,0,0,0,0,0" overrunDistanceUnit="MM" placement="0" placementFlags="10" polygonPlacementFlags="2" predefinedPositionOrder="TR,TL,BR,BL,R,L,TSR,BSR" preserveRotation="1" prioritization="PreferCloser" priority="7" quadOffset="4" repeatDistance="0" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0" repeatDistanceUnits="MM" rotationAngle="0" rotationUnit="AngleDegrees" xOffset="0" yOffset="0" obstacle="1" obstacleFactor="1" />
              <rendering drawLabels="1" fontLimitPixelSize="0" fontMaxPixelSize="10000" fontMinPixelSize="3" limitNumLabels="0" maxNumLabels="2000" mergeLines="1" minFeatureSize="0" obstacle="1" obstacleFactor="1" obstacleType="1" scaleMax="0" scaleMin="0" scaleVisibility="0" unplacedVisibility="0" upsidedownLabels="0" zIndex="7" displayAll="0" />
              <dd_properties>
                <Option type="Map">
                  <Option name="name" type="QString" value="" />
                  <Option name="properties" />
                  <Option name="type" type="QString" value="collection" />
                </Option>
              </dd_properties>
              <callout type="simple">
                <Option type="Map">
                  <Option name="anchorPoint" type="QString" value="pole_of_inaccessibility" />
                  <Option name="blendMode" type="int" value="0" />
                  <Option name="ddProperties" type="Map">
                    <Option name="name" type="QString" value="" />
                    <Option name="properties" />
                    <Option name="type" type="QString" value="collection" />
                  </Option>
                  <Option name="drawToAllParts" type="bool" value="false" />
                  <Option name="enabled" type="QString" value="1" />
                  <Option name="labelAnchorPoint" type="QString" value="point_on_exterior" />
                  <Option name="lineSymbol" type="QString" value="&lt;symbol alpha=&quot;1&quot; clip_to_extent=&quot;1&quot; force_rhr=&quot;0&quot; frame_rate=&quot;10&quot; is_animated=&quot;0&quot; name=&quot;symbol&quot; type=&quot;line&quot;&gt;&lt;data_defined_properties&gt;&lt;Option type=&quot;Map&quot;&gt;&lt;Option name=&quot;name&quot; type=&quot;QString&quot; value=&quot;&quot;/&gt;&lt;Option name=&quot;properties&quot;/&gt;&lt;Option name=&quot;type&quot; type=&quot;QString&quot; value=&quot;collection&quot;/&gt;&lt;/Option&gt;&lt;/data_defined_properties&gt;&lt;layer class=&quot;SimpleLine&quot; enabled=&quot;1&quot; id=&quot;{97983909-6ea7-4356-87c8-e0e5b4ed3686}&quot; locked=&quot;0&quot; pass=&quot;0&quot;&gt;&lt;Option type=&quot;Map&quot;&gt;&lt;Option name=&quot;align_dash_pattern&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;capstyle&quot; type=&quot;QString&quot; value=&quot;square&quot;/&gt;&lt;Option name=&quot;customdash&quot; type=&quot;QString&quot; value=&quot;5;2&quot;/&gt;&lt;Option name=&quot;customdash_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;customdash_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;dash_pattern_offset&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;dash_pattern_offset_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;dash_pattern_offset_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;draw_inside_polygon&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;joinstyle&quot; type=&quot;QString&quot; value=&quot;bevel&quot;/&gt;&lt;Option name=&quot;line_color&quot; type=&quot;QString&quot; value=&quot;60,60,60,255,rgb:0.2352941,0.2352941,0.2352941,1&quot;/&gt;&lt;Option name=&quot;line_style&quot; type=&quot;QString&quot; value=&quot;solid&quot;/&gt;&lt;Option name=&quot;line_width&quot; type=&quot;QString&quot; value=&quot;0.25&quot;/&gt;&lt;Option name=&quot;line_width_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;offset&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;offset_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;offset_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;ring_filter&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;trim_distance_end&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;trim_distance_end_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;trim_distance_end_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;trim_distance_start&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;trim_distance_start_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;trim_distance_start_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;tweak_dash_pattern_on_corners&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;use_custom_dash&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;width_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;/Option&gt;&lt;data_defined_properties&gt;&lt;Option type=&quot;Map&quot;&gt;&lt;Option name=&quot;name&quot; type=&quot;QString&quot; value=&quot;&quot;/&gt;&lt;Option name=&quot;properties&quot;/&gt;&lt;Option name=&quot;type&quot; type=&quot;QString&quot; value=&quot;collection&quot;/&gt;&lt;/Option&gt;&lt;/data_defined_properties&gt;&lt;/layer&gt;&lt;/symbol&gt;" />
                  <Option name="minLength" type="double" value="0" />
                  <Option name="minLengthMapUnitScale" type="QString" value="3x:0,0,0,0,0,0" />
                  <Option name="minLengthUnit" type="QString" value="MM" />
                  <Option name="offsetFromAnchor" type="double" value="0" />
                  <Option name="offsetFromAnchorMapUnitScale" type="QString" value="3x:0,0,0,0,0,0" />
                  <Option name="offsetFromAnchorUnit" type="QString" value="MM" />
                  <Option name="offsetFromLabel" type="double" value="0" />
                  <Option name="offsetFromLabelMapUnitScale" type="QString" value="3x:0,0,0,0,0,0" />
                  <Option name="offsetFromLabelUnit" type="QString" value="MM" />
                </Option>
              </callout>
            </settings>
          </rule>
          <rule filter="&quot;level&quot; = 3 AND &quot;redundant_with_parent&quot; = false AND (&quot;name&quot; != &quot;parent_name&quot; OR &quot;parent_name&quot; IS NULL)" key="{44afe18c-a67a-42b1-9550-1cc1c6299e6d}" description="Level 3 - Sub-debatten" active="1">
            <settings calloutType="simple" priority="5" zIndex="5">
              <text-style allowHtml="0" blendMode="0" capitalization="0" fieldName="name" fontFamily="Libre Caslon Text" fontItalic="0" fontKerning="1" fontLetterSpacing="0" fontSize="8" fontSizeMapUnitScale="3x:0,0,0,0,0,0" fontSizeUnit="Point" fontStrikeout="0" fontUnderline="0" fontWeight="400" fontWordSpacing="0" forcedBold="0" forcedItalic="0" isExpression="0" legendString="Aa" multilineHeight="1" multilineHeightUnit="Percentage" namedStyle="Regular" previewBkgrdColor="255,255,255,255,rgb:1,1,1,1" stretchFactor="100" tabStopDistance="80" tabStopDistanceMapUnitScale="3x:0,0,0,0,0,0" tabStopDistanceUnit="Point" textColor="45,58,82,255,rgb:0.176,0.227,0.322,1" textOpacity="1" textOrientation="horizontal" useSubstitutions="0">
                <families />
                <text-buffer bufferBlendMode="0" bufferColor="242,239,231,255,rgb:0.9490196,0.9372549,0.9058824,1" bufferDraw="0" bufferJoinStyle="128" bufferNoFill="1" bufferOpacity="0.505" bufferSize="0.5" bufferSizeMapUnitScale="3x:0,0,0,0,0,0" bufferSizeUnits="MM" />
                <text-mask maskEnabled="0" maskJoinStyle="128" maskOpacity="1" maskSize="1.5" maskSize2="1.5" maskSizeMapUnitScale="3x:0,0,0,0,0,0" maskSizeUnits="MM" maskType="0" maskedSymbolLayers="" />
                <background shapeBlendMode="0" shapeBorderColor="120,135,160,180,rgb:0.471,0.529,0.627,0.70" shapeBorderWidth="0.20" shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeBorderWidthUnit="MM" shapeDraw="1" shapeFillColor="238,242,248,215,rgb:0.933,0.949,0.973,0.84" shapeJoinStyle="64" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeOffsetUnit="Point" shapeOffsetX="0" shapeOffsetY="0" shapeOpacity="0.82" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeRadiiUnit="MM" shapeRadiiX="0.6" shapeRadiiY="0.6" shapeRotation="0" shapeRotationType="0" shapeSVGFile="" shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeSizeType="0" shapeSizeUnit="MM" shapeSizeX="1.4" shapeSizeY="0.9" shapeType="0">
                  <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="markerSymbol" type="marker">
                    <data_defined_properties>
                      <Option type="Map">
                        <Option name="name" type="QString" value="" />
                        <Option name="properties" />
                        <Option name="type" type="QString" value="collection" />
                      </Option>
                    </data_defined_properties>
                    <layer class="SimpleMarker" enabled="1" id="" locked="0" pass="0">
                      <Option type="Map">
                        <Option name="angle" type="QString" value="0" />
                        <Option name="cap_style" type="QString" value="square" />
                        <Option name="color" type="QString" value="141,90,153,255,rgb:0.5529412,0.3529412,0.6,1" />
                        <Option name="horizontal_anchor_point" type="QString" value="1" />
                        <Option name="joinstyle" type="QString" value="bevel" />
                        <Option name="name" type="QString" value="circle" />
                        <Option name="offset" type="QString" value="0,0" />
                        <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                        <Option name="offset_unit" type="QString" value="MM" />
                        <Option name="outline_color" type="QString" value="35,35,35,255,rgb:0.1372549,0.1372549,0.1372549,1" />
                        <Option name="outline_style" type="QString" value="solid" />
                        <Option name="outline_width" type="QString" value="0" />
                        <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                        <Option name="outline_width_unit" type="QString" value="MM" />
                        <Option name="scale_method" type="QString" value="diameter" />
                        <Option name="size" type="QString" value="2" />
                        <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                        <Option name="size_unit" type="QString" value="MM" />
                        <Option name="vertical_anchor_point" type="QString" value="1" />
                      </Option>
                      <data_defined_properties>
                        <Option type="Map">
                          <Option name="name" type="QString" value="" />
                          <Option name="properties" />
                          <Option name="type" type="QString" value="collection" />
                        </Option>
                      </data_defined_properties>
                    </layer>
                  </symbol>
                  <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="fillSymbol" type="fill">
                    <data_defined_properties>
                      <Option type="Map">
                        <Option name="name" type="QString" value="" />
                        <Option name="properties" />
                        <Option name="type" type="QString" value="collection" />
                      </Option>
                    </data_defined_properties>
                    <layer class="SimpleFill" enabled="1" id="" locked="0" pass="0">
                      <Option type="Map">
                        <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                        <Option name="color" type="QString" value="238,242,248,215,rgb:0.933,0.949,0.973,0.84" />
                        <Option name="joinstyle" type="QString" value="bevel" />
                        <Option name="offset" type="QString" value="0,0" />
                        <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                        <Option name="offset_unit" type="QString" value="MM" />
                        <Option name="outline_color" type="QString" value="120,135,160,180,rgb:0.471,0.529,0.627,0.70" />
                        <Option name="outline_style" type="QString" value="solid" />
                        <Option name="outline_width" type="QString" value="0.20" />
                        <Option name="outline_width_unit" type="QString" value="MM" />
                        <Option name="style" type="QString" value="solid" />
                      </Option>
                      <data_defined_properties>
                        <Option type="Map">
                          <Option name="name" type="QString" value="" />
                          <Option name="properties" />
                          <Option name="type" type="QString" value="collection" />
                        </Option>
                      </data_defined_properties>
                    </layer>
                  </symbol>
                </background>
                <shadow shadowBlendMode="6" shadowColor="30,25,20,255,rgb:0.117,0.098,0.078,1" shadowDraw="1" shadowOffsetAngle="90" shadowOffsetDist="0.4" shadowOffsetGlobal="1" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowOffsetUnit="MM" shadowOpacity="0.12" shadowRadius="1.0" shadowRadiusAlphaOnly="0" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowRadiusUnit="MM" shadowScale="100" shadowUnder="1" />
                <dd_properties>
                  <Option type="Map">
                    <Option name="name" type="QString" value="" />
                    <Option name="properties" />
                    <Option name="type" type="QString" value="collection" />
                  </Option>
                </dd_properties>
                <substitutions />
              </text-style>
              <text-format addDirectionSymbol="0" autoWrapLength="0" decimals="3" formatNumbers="0" leftDirectionSymbol="&lt;" multilineAlign="3" placeDirectionSymbol="0" plussign="0" reverseDirectionSymbol="0" rightDirectionSymbol="&gt;" useMaxLineLengthForAutoWrap="1" wrapChar="" />
              <placement allowDegraded="0" centroidInside="0" centroidWhole="0" dist="1.2" distMapUnitScale="3x:0,0,0,0,0,0" distUnits="MM" fitInPolygonOnly="0" geometryGenerator="" geometryGeneratorEnabled="0" geometryGeneratorType="PointGeometry" labelOffsetMapUnitScale="3x:0,0,0,0,0,0" layerType="PolygonGeometry" lineAnchorClipping="0" lineAnchorPercent="0.5" lineAnchorTextPoint="FollowPlacement" lineAnchorType="0" maxCurvedCharAngleIn="25" maxCurvedCharAngleOut="-25" maximumDistance="0" maximumDistanceMapUnitScale="3x:0,0,0,0,0,0" maximumDistanceUnit="MM" multipartBehavior="LabelLargestPartOnly" offsetType="0" offsetUnits="MM" overlapHandling="PreventOverlap" overrunDistance="0" overrunDistanceMapUnitScale="3x:0,0,0,0,0,0" overrunDistanceUnit="MM" placement="0" placementFlags="10" polygonPlacementFlags="2" predefinedPositionOrder="TR,TL,BR,BL,R,L,TSR,BSR" preserveRotation="1" prioritization="PreferCloser" priority="3" quadOffset="4" repeatDistance="0" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0" repeatDistanceUnits="MM" rotationAngle="0" rotationUnit="AngleDegrees" xOffset="0" yOffset="0" obstacle="1" obstacleFactor="1" />
              <rendering drawLabels="1" fontLimitPixelSize="0" fontMaxPixelSize="10000" fontMinPixelSize="3" limitNumLabels="0" maxNumLabels="2000" mergeLines="1" minFeatureSize="0" obstacle="1" obstacleFactor="1" obstacleType="1" scaleMax="0" scaleMin="0" scaleVisibility="0" unplacedVisibility="0" upsidedownLabels="0" zIndex="3" displayAll="0" />
              <dd_properties>
                <Option type="Map">
                  <Option name="name" type="QString" value="" />
                  <Option name="properties" />
                  <Option name="type" type="QString" value="collection" />
                </Option>
              </dd_properties>
              <callout type="simple">
                <Option type="Map">
                  <Option name="anchorPoint" type="QString" value="pole_of_inaccessibility" />
                  <Option name="blendMode" type="int" value="0" />
                  <Option name="ddProperties" type="Map">
                    <Option name="name" type="QString" value="" />
                    <Option name="properties" />
                    <Option name="type" type="QString" value="collection" />
                  </Option>
                  <Option name="drawToAllParts" type="bool" value="false" />
                  <Option name="enabled" type="QString" value="1" />
                  <Option name="labelAnchorPoint" type="QString" value="point_on_exterior" />
                  <Option name="lineSymbol" type="QString" value="&lt;symbol alpha=&quot;1&quot; clip_to_extent=&quot;1&quot; force_rhr=&quot;0&quot; frame_rate=&quot;10&quot; is_animated=&quot;0&quot; name=&quot;symbol&quot; type=&quot;line&quot;&gt;&lt;data_defined_properties&gt;&lt;Option type=&quot;Map&quot;&gt;&lt;Option name=&quot;name&quot; type=&quot;QString&quot; value=&quot;&quot;/&gt;&lt;Option name=&quot;properties&quot;/&gt;&lt;Option name=&quot;type&quot; type=&quot;QString&quot; value=&quot;collection&quot;/&gt;&lt;/Option&gt;&lt;/data_defined_properties&gt;&lt;layer class=&quot;SimpleLine&quot; enabled=&quot;1&quot; id=&quot;{ef436c40-1fdf-4a8d-8b47-943e2b133e4b}&quot; locked=&quot;0&quot; pass=&quot;0&quot;&gt;&lt;Option type=&quot;Map&quot;&gt;&lt;Option name=&quot;align_dash_pattern&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;capstyle&quot; type=&quot;QString&quot; value=&quot;square&quot;/&gt;&lt;Option name=&quot;customdash&quot; type=&quot;QString&quot; value=&quot;5;2&quot;/&gt;&lt;Option name=&quot;customdash_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;customdash_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;dash_pattern_offset&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;dash_pattern_offset_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;dash_pattern_offset_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;draw_inside_polygon&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;joinstyle&quot; type=&quot;QString&quot; value=&quot;bevel&quot;/&gt;&lt;Option name=&quot;line_color&quot; type=&quot;QString&quot; value=&quot;60,60,60,255,rgb:0.2352941,0.2352941,0.2352941,1&quot;/&gt;&lt;Option name=&quot;line_style&quot; type=&quot;QString&quot; value=&quot;solid&quot;/&gt;&lt;Option name=&quot;line_width&quot; type=&quot;QString&quot; value=&quot;0.25&quot;/&gt;&lt;Option name=&quot;line_width_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;offset&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;offset_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;offset_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;ring_filter&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;trim_distance_end&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;trim_distance_end_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;trim_distance_end_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;trim_distance_start&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;trim_distance_start_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;trim_distance_start_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;tweak_dash_pattern_on_corners&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;use_custom_dash&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;width_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;/Option&gt;&lt;data_defined_properties&gt;&lt;Option type=&quot;Map&quot;&gt;&lt;Option name=&quot;name&quot; type=&quot;QString&quot; value=&quot;&quot;/&gt;&lt;Option name=&quot;properties&quot;/&gt;&lt;Option name=&quot;type&quot; type=&quot;QString&quot; value=&quot;collection&quot;/&gt;&lt;/Option&gt;&lt;/data_defined_properties&gt;&lt;/layer&gt;&lt;/symbol&gt;" />
                  <Option name="minLength" type="double" value="0" />
                  <Option name="minLengthMapUnitScale" type="QString" value="3x:0,0,0,0,0,0" />
                  <Option name="minLengthUnit" type="QString" value="MM" />
                  <Option name="offsetFromAnchor" type="double" value="0" />
                  <Option name="offsetFromAnchorMapUnitScale" type="QString" value="3x:0,0,0,0,0,0" />
                  <Option name="offsetFromAnchorUnit" type="QString" value="MM" />
                  <Option name="offsetFromLabel" type="double" value="0" />
                  <Option name="offsetFromLabelMapUnitScale" type="QString" value="3x:0,0,0,0,0,0" />
                  <Option name="offsetFromLabelUnit" type="QString" value="MM" />
                </Option>
              </callout>
            </settings>
          </rule>
          <rule filter="&quot;level&quot; = 4 AND &quot;redundant_with_parent&quot; = false AND (&quot;name&quot; != &quot;parent_name&quot; OR &quot;parent_name&quot; IS NULL)" key="{525b4999-8e8d-4e4d-867f-f723614c2ad2}" description="Level 4 - Micro-debatten" active="1">
            <settings calloutType="simple" priority="3" zIndex="3">
              <text-style allowHtml="0" blendMode="0" capitalization="0" fieldName="name" fontFamily="Libre Caslon Text" fontItalic="0" fontKerning="1" fontLetterSpacing="0" fontSize="6.5" fontSizeMapUnitScale="3x:0,0,0,0,0,0" fontSizeUnit="Point" fontStrikeout="0" fontUnderline="0" fontWeight="400" fontWordSpacing="0" forcedBold="0" forcedItalic="0" isExpression="0" legendString="Aa" multilineHeight="1" multilineHeightUnit="Percentage" namedStyle="Regular" previewBkgrdColor="255,255,255,255,rgb:1,1,1,1" stretchFactor="100" tabStopDistance="80" tabStopDistanceMapUnitScale="3x:0,0,0,0,0,0" tabStopDistanceUnit="Point" textColor="55,68,92,255,rgb:0.215,0.266,0.360,1" textOpacity="1" textOrientation="horizontal" useSubstitutions="0">
                <families />
                <text-buffer bufferBlendMode="0" bufferColor="242,239,231,255,rgb:0.9490196,0.9372549,0.9058824,1" bufferDraw="0" bufferJoinStyle="128" bufferNoFill="1" bufferOpacity="0.51100000000000001" bufferSize="0.40000000000000002" bufferSizeMapUnitScale="3x:0,0,0,0,0,0" bufferSizeUnits="MM" />
                <text-mask maskEnabled="0" maskJoinStyle="128" maskOpacity="1" maskSize="1.5" maskSize2="1.5" maskSizeMapUnitScale="3x:0,0,0,0,0,0" maskSizeUnits="MM" maskType="0" maskedSymbolLayers="" />
                <background shapeBlendMode="0" shapeBorderColor="140,152,175,160,rgb:0.549,0.596,0.686,0.62" shapeBorderWidth="0.16" shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeBorderWidthUnit="MM" shapeDraw="1" shapeFillColor="242,245,250,205,rgb:0.949,0.960,0.980,0.80" shapeJoinStyle="64" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeOffsetUnit="Point" shapeOffsetX="0" shapeOffsetY="0" shapeOpacity="0.82" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeRadiiUnit="MM" shapeRadiiX="0.5" shapeRadiiY="0.5" shapeRotation="0" shapeRotationType="0" shapeSVGFile="" shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeSizeType="0" shapeSizeUnit="MM" shapeSizeX="1.2" shapeSizeY="0.7" shapeType="0">
                  <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="markerSymbol" type="marker">
                    <data_defined_properties>
                      <Option type="Map">
                        <Option name="name" type="QString" value="" />
                        <Option name="properties" />
                        <Option name="type" type="QString" value="collection" />
                      </Option>
                    </data_defined_properties>
                    <layer class="SimpleMarker" enabled="1" id="" locked="0" pass="0">
                      <Option type="Map">
                        <Option name="angle" type="QString" value="0" />
                        <Option name="cap_style" type="QString" value="square" />
                        <Option name="color" type="QString" value="141,90,153,255,rgb:0.5529412,0.3529412,0.6,1" />
                        <Option name="horizontal_anchor_point" type="QString" value="1" />
                        <Option name="joinstyle" type="QString" value="bevel" />
                        <Option name="name" type="QString" value="circle" />
                        <Option name="offset" type="QString" value="0,0" />
                        <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                        <Option name="offset_unit" type="QString" value="MM" />
                        <Option name="outline_color" type="QString" value="35,35,35,255,rgb:0.1372549,0.1372549,0.1372549,1" />
                        <Option name="outline_style" type="QString" value="solid" />
                        <Option name="outline_width" type="QString" value="0" />
                        <Option name="outline_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                        <Option name="outline_width_unit" type="QString" value="MM" />
                        <Option name="scale_method" type="QString" value="diameter" />
                        <Option name="size" type="QString" value="2" />
                        <Option name="size_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                        <Option name="size_unit" type="QString" value="MM" />
                        <Option name="vertical_anchor_point" type="QString" value="1" />
                      </Option>
                      <data_defined_properties>
                        <Option type="Map">
                          <Option name="name" type="QString" value="" />
                          <Option name="properties" />
                          <Option name="type" type="QString" value="collection" />
                        </Option>
                      </data_defined_properties>
                    </layer>
                  </symbol>
                  <symbol alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0" name="fillSymbol" type="fill">
                    <data_defined_properties>
                      <Option type="Map">
                        <Option name="name" type="QString" value="" />
                        <Option name="properties" />
                        <Option name="type" type="QString" value="collection" />
                      </Option>
                    </data_defined_properties>
                    <layer class="SimpleFill" enabled="1" id="" locked="0" pass="0">
                      <Option type="Map">
                        <Option name="border_width_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                        <Option name="color" type="QString" value="242,245,250,205,rgb:0.949,0.960,0.980,0.80" />
                        <Option name="joinstyle" type="QString" value="bevel" />
                        <Option name="offset" type="QString" value="0,0" />
                        <Option name="offset_map_unit_scale" type="QString" value="3x:0,0,0,0,0,0" />
                        <Option name="offset_unit" type="QString" value="MM" />
                        <Option name="outline_color" type="QString" value="140,152,175,160,rgb:0.549,0.596,0.686,0.62" />
                        <Option name="outline_style" type="QString" value="solid" />
                        <Option name="outline_width" type="QString" value="0.16" />
                        <Option name="outline_width_unit" type="QString" value="MM" />
                        <Option name="style" type="QString" value="solid" />
                      </Option>
                      <data_defined_properties>
                        <Option type="Map">
                          <Option name="name" type="QString" value="" />
                          <Option name="properties" />
                          <Option name="type" type="QString" value="collection" />
                        </Option>
                      </data_defined_properties>
                    </layer>
                  </symbol>
                </background>
                <shadow shadowBlendMode="6" shadowColor="30,25,20,255,rgb:0.117,0.098,0.078,1" shadowDraw="1" shadowOffsetAngle="90" shadowOffsetDist="0.4" shadowOffsetGlobal="1" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowOffsetUnit="MM" shadowOpacity="0.10" shadowRadius="1.0" shadowRadiusAlphaOnly="0" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowRadiusUnit="MM" shadowScale="100" shadowUnder="1" />
                <dd_properties>
                  <Option type="Map">
                    <Option name="name" type="QString" value="" />
                    <Option name="properties" />
                    <Option name="type" type="QString" value="collection" />
                  </Option>
                </dd_properties>
                <substitutions />
              </text-style>
              <text-format addDirectionSymbol="0" autoWrapLength="0" decimals="3" formatNumbers="0" leftDirectionSymbol="&lt;" multilineAlign="3" placeDirectionSymbol="0" plussign="0" reverseDirectionSymbol="0" rightDirectionSymbol="&gt;" useMaxLineLengthForAutoWrap="1" wrapChar="" />
              <placement allowDegraded="0" centroidInside="0" centroidWhole="0" dist="1.2" distMapUnitScale="3x:0,0,0,0,0,0" distUnits="MM" fitInPolygonOnly="0" geometryGenerator="" geometryGeneratorEnabled="0" geometryGeneratorType="PointGeometry" labelOffsetMapUnitScale="3x:0,0,0,0,0,0" layerType="PolygonGeometry" lineAnchorClipping="0" lineAnchorPercent="0.5" lineAnchorTextPoint="FollowPlacement" lineAnchorType="0" maxCurvedCharAngleIn="25" maxCurvedCharAngleOut="-25" maximumDistance="0" maximumDistanceMapUnitScale="3x:0,0,0,0,0,0" maximumDistanceUnit="MM" multipartBehavior="LabelLargestPartOnly" offsetType="0" offsetUnits="MM" overlapHandling="PreventOverlap" overrunDistance="0" overrunDistanceMapUnitScale="3x:0,0,0,0,0,0" overrunDistanceUnit="MM" placement="0" placementFlags="10" polygonPlacementFlags="2" predefinedPositionOrder="TR,TL,BR,BL,R,L,TSR,BSR" preserveRotation="1" prioritization="PreferCloser" priority="3" quadOffset="4" repeatDistance="0" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0" repeatDistanceUnits="MM" rotationAngle="0" rotationUnit="AngleDegrees" xOffset="0" yOffset="0" obstacle="1" obstacleFactor="1" />
              <rendering drawLabels="1" fontLimitPixelSize="0" fontMaxPixelSize="10000" fontMinPixelSize="3" limitNumLabels="0" maxNumLabels="2000" mergeLines="1" minFeatureSize="0" obstacle="1" obstacleFactor="1" obstacleType="1" scaleMax="0" scaleMin="0" scaleVisibility="0" unplacedVisibility="0" upsidedownLabels="0" zIndex="3" displayAll="0" />
              <dd_properties>
                <Option type="Map">
                  <Option name="name" type="QString" value="" />
                  <Option name="properties" />
                  <Option name="type" type="QString" value="collection" />
                </Option>
              </dd_properties>
              <callout type="simple">
                <Option type="Map">
                  <Option name="anchorPoint" type="QString" value="pole_of_inaccessibility" />
                  <Option name="blendMode" type="int" value="0" />
                  <Option name="ddProperties" type="Map">
                    <Option name="name" type="QString" value="" />
                    <Option name="properties" />
                    <Option name="type" type="QString" value="collection" />
                  </Option>
                  <Option name="drawToAllParts" type="bool" value="false" />
                  <Option name="enabled" type="QString" value="0" />
                  <Option name="labelAnchorPoint" type="QString" value="point_on_exterior" />
                  <Option name="lineSymbol" type="QString" value="&lt;symbol alpha=&quot;1&quot; clip_to_extent=&quot;1&quot; force_rhr=&quot;0&quot; frame_rate=&quot;10&quot; is_animated=&quot;0&quot; name=&quot;symbol&quot; type=&quot;line&quot;&gt;&lt;data_defined_properties&gt;&lt;Option type=&quot;Map&quot;&gt;&lt;Option name=&quot;name&quot; type=&quot;QString&quot; value=&quot;&quot;/&gt;&lt;Option name=&quot;properties&quot;/&gt;&lt;Option name=&quot;type&quot; type=&quot;QString&quot; value=&quot;collection&quot;/&gt;&lt;/Option&gt;&lt;/data_defined_properties&gt;&lt;layer class=&quot;SimpleLine&quot; enabled=&quot;1&quot; id=&quot;{1cd783a0-4aa3-44b6-af7f-ceb82e8db608}&quot; locked=&quot;0&quot; pass=&quot;0&quot;&gt;&lt;Option type=&quot;Map&quot;&gt;&lt;Option name=&quot;align_dash_pattern&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;capstyle&quot; type=&quot;QString&quot; value=&quot;square&quot;/&gt;&lt;Option name=&quot;customdash&quot; type=&quot;QString&quot; value=&quot;5;2&quot;/&gt;&lt;Option name=&quot;customdash_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;customdash_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;dash_pattern_offset&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;dash_pattern_offset_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;dash_pattern_offset_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;draw_inside_polygon&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;joinstyle&quot; type=&quot;QString&quot; value=&quot;bevel&quot;/&gt;&lt;Option name=&quot;line_color&quot; type=&quot;QString&quot; value=&quot;60,60,60,255,rgb:0.2352941,0.2352941,0.2352941,1&quot;/&gt;&lt;Option name=&quot;line_style&quot; type=&quot;QString&quot; value=&quot;solid&quot;/&gt;&lt;Option name=&quot;line_width&quot; type=&quot;QString&quot; value=&quot;0.3&quot;/&gt;&lt;Option name=&quot;line_width_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;offset&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;offset_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;offset_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;ring_filter&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;trim_distance_end&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;trim_distance_end_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;trim_distance_end_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;trim_distance_start&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;trim_distance_start_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;Option name=&quot;trim_distance_start_unit&quot; type=&quot;QString&quot; value=&quot;MM&quot;/&gt;&lt;Option name=&quot;tweak_dash_pattern_on_corners&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;use_custom_dash&quot; type=&quot;QString&quot; value=&quot;0&quot;/&gt;&lt;Option name=&quot;width_map_unit_scale&quot; type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot;/&gt;&lt;/Option&gt;&lt;data_defined_properties&gt;&lt;Option type=&quot;Map&quot;&gt;&lt;Option name=&quot;name&quot; type=&quot;QString&quot; value=&quot;&quot;/&gt;&lt;Option name=&quot;properties&quot;/&gt;&lt;Option name=&quot;type&quot; type=&quot;QString&quot; value=&quot;collection&quot;/&gt;&lt;/Option&gt;&lt;/data_defined_properties&gt;&lt;/layer&gt;&lt;/symbol&gt;" />
                  <Option name="minLength" type="double" value="0" />
                  <Option name="minLengthMapUnitScale" type="QString" value="3x:0,0,0,0,0,0" />
                  <Option name="minLengthUnit" type="QString" value="MM" />
                  <Option name="offsetFromAnchor" type="double" value="0" />
                  <Option name="offsetFromAnchorMapUnitScale" type="QString" value="3x:0,0,0,0,0,0" />
                  <Option name="offsetFromAnchorUnit" type="QString" value="MM" />
                  <Option name="offsetFromLabel" type="double" value="0" />
                  <Option name="offsetFromLabelMapUnitScale" type="QString" value="3x:0,0,0,0,0,0" />
                  <Option name="offsetFromLabelUnit" type="QString" value="MM" />
                </Option>
              </callout>
            </settings>
          </rule>
        </rules>
      </labeling>
      <blendMode>0</blendMode>
      <featureBlendMode>6</featureBlendMode>
      </qgis>