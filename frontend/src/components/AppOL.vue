<template>
  <div style="background-color: orange; height: 600px">

    <!-- ========== map & view ========= -->
    <vl-map  :load-tiles-while-animating="true"
             :load-tiles-while-interacting="true"
             data-projection="EPSG:4326"
             ref="map"
              @mounted="onMapMounted"
           >

    <vl-view ref="view"
             :zoom.sync="zoom"
             :center.sync="center"
             :rotation.sync="rotation"></vl-view>

      <!-- ========== layers ========= -->
      <!-- OpenStreetMap base layer
      -->
      <vl-layer-tile id="osm">
        <vl-source-osm></vl-source-osm>
      </vl-layer-tile>

      <!-- flight path features layer - geojson file retrieval via url
          TODO: swap out default url loader for custom loader (for error checking)
          almost: https://github.com/ghettovoice/vuelayers/issues/59
          uses style function/factory to color item based on geojson properties

      -->
      <vl-layer-vector >
        <vl-source-vector  :url="geojsonUrl"
                           :features.sync="geojFeatures" />

        <vl-style-func :factory="geojStyleFuncFactory"></vl-style-func>
      </vl-layer-vector>

      <!-- kml features layer
      -->
      <vl-layer-vector >
          <vl-source-vector :url="kmlUrl"
                            :format-factory="kmlFormatFactory" />
      </vl-layer-vector>

      <!-- asdex layer ==========================  -->
      <vl-layer-vector >

<!-- note: PostGIS put id (which is track num) in geojson at the same
     level with type and geometry which allows this to work: -->

<!-- ============ use loader-factory ============ -->
        <vl-source-vector
                  :url="asdexUrl"
                  :features.sync="asdexFeatures"
                  :loader-factory="loaderFactoryOuter"
                  />

       <vl-style-func :factory="asdexStyleFuncFac" />

<!-- ======================================================= -->

      </vl-layer-vector>

      <!-- ========== popup =========
          note: 'display' string in geojson properties was crafted by python
      -->
   <vl-interaction-select :features.sync="geojFeatures"></vl-interaction-select>

    <vl-overlay v-for="feature in geojFeatures"
                :key="feature.id"
                :position="feature.geometry.coordinates[0]">
      <div style="background: #ccf">
        {{ feature.properties.display }}
      </div>
    </vl-overlay>

      <!-- ========== end layers ========= -->
    </vl-map>

  </div>
</template>

<script>

// $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

import ZoomSlider from 'ol/control/ZoomSlider'
import ScaleLine  from 'ol/control/ScaleLine'
import KML        from 'ol/format/KML'

import Stroke     from 'ol/style/Stroke'
import Style      from 'ol/style/Style'
import Text       from 'ol/style/Text'
import Fill       from 'ol/style/Fill'
import Circle     from 'ol/style/Circle'

import { Vector as VectorLayer } from 'ol/layer'

// ==========================================================

// -------------- linestrings
const plainStyle  =new Style({ stroke: new Stroke({ color: 'purple', width: 3.0 }) })

// -------------- unused linestrings (was going to be source_type)
const src_s_style =new Style({ stroke: new Stroke({ color: 'green',  width: 3.0 }) })
const src_f_style =new Style({ stroke: new Stroke({ color: 'blue',   width: 3.0 }) })
const src_a_style =new Style({ stroke: new Stroke({ color: 'magenta',width: 3.0 }) })
const unk_style   =new Style({ stroke: new Stroke({ color: 'brown',  width: 3.0 }) })

// -------------- target circles (Style needs (dynamic) acid)
const image_circle = new Circle({ radius: 10,
                             fill: new Fill({ color: '#fff', }),
                             stroke: new Stroke({ color: '#F44336', }),   })
const image_h_circle = new Circle({ radius: 15,
                             fill: new Fill({ color: 'yellow', }),
                             stroke: new Stroke({ color: 'green', }),   })
// ==================================================================================

const tgt_offs = 900000;  // added to target id (track) to get linestring id

const methods = {

    // ==========================================================
    norm_tgt_Style(acid) {
        return new Style({
          image: image_circle,
          text: new Text({ text: String(acid), }),
        })},

    high_tgt_Style(acid) {
        return new Style({
          image: image_h_circle,
          text: new Text({ text: String(acid) }),
        })},
    // ==========================================================
    // https://firstclassjs.com/remove-duplicate-objects-from-javascript-array-how-to-performance-comparison/
    // TypeError: array.filter is not a function
    removeDuplicates_2(array, key) {
        return array.filter((obj, index, self) =>
            index === self.findIndex((el) => (
                el[key] === obj[key]
            ))
        )
    },

    // ==========================================================
    //  WARNING: this ONLY works on a specific version of vuelayers:
    //   package.json:    "vuelayers": "0.11.22"

    loaderFactoryOuter() {
      return (extent, resolution, projection) => this.loaderFactoryInner(
                                                  extent, resolution, projection)
    },

    loaderFactoryInner(extent, resolution, projection) {
console.log("lint" + extent+ resolution+ projection)
console.log("new fetch");
      //return fetch(this.asdexUrl)
      //  .then(response => response.json())

        return fetch(this.asdexUrl , {
          mode: 'cors'
        }
        ).then(response => response.json())

        .then(data =>  {

          // clean up data
          // NOTE: but ONLY for the Points, not the LineStrings
          // which is track/id < 900000

          let dlist = [];
          for (let k = 0; k < data.features.length; k++) {
              if (data.features[k].id < tgt_offs) {
                  let elem = { track:  data.features[k].properties.track,
                               acid:   data.features[k].properties.acid,
                               actype: data.features[k].properties.actype  };
                  dlist.push(elem);
              }
          }

          // ---------------------------------
          const sortedlist = dlist.sort(function(a, b) {
              if (a.acid < b.acid) { return -1; }
              if (a.acid > b.acid) { return  1; }
              return 0;
            });
          // ---------------------------------

          this.$root.$emit('dlist', (sortedlist) );

console.log("returning data:");
console.log(data);

          return(data);
       })
    },

    onMapMounted () {
      // now ol.Map instance is ready and we can work with it directly
      this.$refs.map.$map.getControls().extend([
        new ScaleLine(),
        new ZoomSlider(),
      ])
    },

    kmlFormatFactory () {
      return new KML()
    },

    // ------------ ASDEX attempt to color lines
    // sun pm: now works all the time, and nothing undefined:
    asdexStyleFuncFac() {

      return (feature) => {
// console.log("aSFF+g:" + feature.get('track') + "," +
//              this.highLightMe + ',' + feature.getGeometry().getType() );

        // ------------------------------

        if (feature.getGeometry().getType() == "Point") {
            if (feature.key == this.highLightMe) {
                return this.high_tgt_Style(feature.get('acid'));
            } else {
                return this.norm_tgt_Style(feature.get('acid'));
            }
        }
        return plainStyle;
     }
    },
    // ------------ attempt to color lines
    geojStyleFuncFactory() {

      return (feature) => {
        if (feature.get('SOURCE_TYPE')) {
          if (feature.get('SOURCE_TYPE')=='S') { return src_s_style; }
          if (feature.get('SOURCE_TYPE')=='F') { return src_f_style; }
          if (feature.get('SOURCE_TYPE')=='A') { return src_a_style; }
          return unk_style;
        }
        return unk_style;
     }
   }
}

// ==========================================================

// center map on center of usa
var KSTL = [-90.3700289, 38.7486972];

export default {
    methods,
    data () {
      return {
        zoom: 5,
        center: KSTL,
        rotation: 0,

        geojsonUrl: '',
        geojFeatures: [],

        kmlUrl: '',

        // all OLD, INOP:
        asdexUrl: 'bogus',
        asdexFeatures: [],
        aaaFeatures: [],   // rather old: https://github.com/ghettovoice/vuelayers/issues/25
        highLightMe: 15,  // track id of item to highlight

        // NEW:
        highlightedFeat: 0
      }
    },

// ==========================================================

  mounted () {

    // ---- receive vuejs message from AppUI, insert query into reactive
    // ---- location which apparently fires off a url request
    // -------------------------
    this.$root.$on('geojsonurl', (the_query) => {
      console.log("geojson:"+the_query);

      // this.geojsonUrl = the_query;   // << that's all we have to do!
      this.geojsonUrl = "https://openlayers.org/en/latest/examples/data/geojson/countries.geojson";
    })
    // -------------------------
    this.$root.$on('kmlurl', (the_query) => {
      console.log("kml:"+the_query);

      this.kmlUrl = the_query;
    })
    // -------------------------
    this.$root.$on('highlightthis', (the_target) => {

      this.highLightMe = the_target;

// ================================  Q: does asdexStyleFuncFac replace this???

      // turn off the previous one:
      if (this.highlightedFeat != 0) {

          let acid = this.highlightedFeat.get('acid');
          this.highlightedFeat.setStyle(this.norm_tgt_Style(acid));
      }

      // find the vector layer that has a Feature with this id
      const a_layer = this.$refs.map.getLayers().filter(layer => {
          return layer instanceof VectorLayer &&
                   layer.getSource().getFeatureById(the_target)
          })

      // --------- this statement causes aSFF to fire with valid arguments
      if (a_layer[0] === undefined) {
          console.log("could not find the_target=" + the_target)
          } else {

          this.highlightedFeat = a_layer[0].getSource().getFeatureById(the_target);

          let acid = this.highlightedFeat.get('acid');
          this.highlightedFeat.setStyle(this.high_tgt_Style(acid));
      }

      // ================================
    })

    // -------------------------
    this.$root.$on('asdexurl', (the_query) => {
      //console.log("asdex::"+the_query);
      let prefix = "http://asdi-db.cssiinc.com:8080/"
      //            http://asdi-db.cssiinc.com:8080/get_asdex?apt=IAD&rand=73246
      // this fires off loaderFactory via vl-source-vector which does the actual fetch
      let url_to_fetch = prefix + the_query;
      console.log(url_to_fetch);
      this.asdexUrl = url_to_fetch;
    })
  }, // ---- mounted

}

</script>

<style lang="scss">
.map {
    height: 90%;
}

