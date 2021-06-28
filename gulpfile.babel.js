import fs from 'fs';
import path from 'path';
import minimist from 'minimist'
import gulp from 'gulp'
import sourcemaps from 'gulp-sourcemaps';
import cleanCSS from 'gulp-clean-css';
import moduleImporter from 'sass-module-importer';
import compilerPackage from 'google-closure-compiler';
import babel from 'gulp-babel'

const sass = require('gulp-sass')(require('sass'));
const closureCompiler = compilerPackage.gulp();

const paths = {
    inBase: './spongeauth/static',
    outBase: './spongeauth/static-build',

    styles: '/styles',
    appStyle: '/styles/app.scss',

    fonts: '/fonts',

    scripts: '/scripts',
    appScript: '/scripts/app.js',

    images: '/images',
};
const production = minimist(process.argv).production || false;

function styles() {
    let pipe = gulp.src(paths.inBase + paths.styles + '/*.scss')
        .pipe(sourcemaps.init())
        .pipe(sass({ importer: moduleImporter() }));

    if (production) {
        pipe = pipe.pipe(cleanCSS());
    }

    return pipe
        .pipe(sourcemaps.write('../maps/'))
        .pipe(gulp.dest(paths.outBase + paths.styles));
}

function fonts() {
    return gulp.src([
        './node_modules/font-awesome/fonts/fontawesome-webfont.*',
        './node_modules/bootstrap-sass/assets/fonts/bootstrap/glyphicons-halflings-regular.*',
    ]).pipe(gulp.dest(paths.outBase + paths.fonts));
}

function images() {
    return gulp.src(paths.inBase + paths.images + '/**')
        .pipe(gulp.dest(paths.outBase + paths.images));
}

const buildExterns = () => {
    const externsDir = './closureexterns';
    const externsFiles = fs.readdirSync(externsDir);
    return externsFiles
        .filter((fn) => fn.endsWith('.js'))
        .map((fn) => path.join(externsDir, fn));
};

function scripts() {
    const compiler = production ? closureCompiler({
        compilationLevel: 'ADVANCED',
        languageIn: 'STABLE',
        languageOut: 'ECMASCRIPT5_STRICT',
        jsOutputFile: 'app.js',
        assumeFunctionWrapper: true,
        outputWrapper: '(function(){%output%}).call(this)',
        externs: buildExterns(),
        warningLevel: 'VERBOSE',
    }) : babel({
        presets: ['@babel/env'],
    });

    return gulp.src(paths.inBase + paths.appScript, {base: './'})
        .pipe(sourcemaps.init())
        .pipe(compiler)
        .pipe(sourcemaps.write('../maps/'))
        .pipe(gulp.dest(paths.outBase + paths.scripts));
}

function watch() {
    gulp.watch(paths.inBase + paths.styles + '/**', styles);
    gulp.watch(paths.inBase + paths.scripts + '/**', scripts);
    gulp.watch(paths.inBase + paths.images + '/**', images);
}

const build = gulp.parallel(styles, fonts, scripts, images);

exports.build = build;
exports.watch = watch;
exports.default = gulp.series(build, watch);
